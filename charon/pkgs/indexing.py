"""
Copyright (C) 2022 Red Hat, Inc. (https://github.com/Commonjava/charon)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from charon.config import get_template
from charon.storage import S3Client
# from charon.cache import CFClient
# from charon.pkgs.pkg_utils import invalidate_cf_paths
from charon.constants import (INDEX_HTML_TEMPLATE, NPM_INDEX_HTML_TEMPLATE,
                              PACKAGE_TYPE_MAVEN, PACKAGE_TYPE_NPM, PROD_INFO_SUFFIX)
from charon.utils.files import digest_content
from jinja2 import Template
import os
import logging
from typing import List, Set, Tuple

from charon.utils.strings import remove_prefix

logger = logging.getLogger(__name__)


def __get_index_template(package_type: str) -> str:
    """Gets the jinja2 template file content for index generation"""
    try:
        return get_template("index.html.j2")
    except FileNotFoundError:
        logger.info("index template file not defined,"
                    " will use default template.")
        if package_type == PACKAGE_TYPE_MAVEN:
            return INDEX_HTML_TEMPLATE
        elif package_type == PACKAGE_TYPE_NPM:
            return NPM_INDEX_HTML_TEMPLATE


MAVEN_INDEX_TEMPLATE = __get_index_template(PACKAGE_TYPE_MAVEN)
NPM_INDEX_TEMPLATE = __get_index_template(PACKAGE_TYPE_NPM)


class IndexedHTML(object):
    # object for holding index html file data
    def __init__(self, title: str, header: str, items: Set[str]):
        self.title = title
        self.header = header
        self.items = items

    def generate_index_file_content(self, package_type: str) -> str:
        if package_type == PACKAGE_TYPE_MAVEN:
            template = Template(MAVEN_INDEX_TEMPLATE)
        elif package_type == PACKAGE_TYPE_NPM:
            template = Template(NPM_INDEX_TEMPLATE)
        return template.render(index=self)


def generate_indexes(
    package_type: str,
    top_level: str,
    changed_dirs: List[str],
    s3_client: S3Client,
    bucket: str,
    prefix: str = None
) -> List[str]:
    if top_level[-1] != '/':
        top_level += '/'

    s3_folders = set()

    # chopp down every lines, left s3 client key format
    for path in changed_dirs:
        path = path.replace(top_level, '')
        if path.startswith("/"):
            path = path[1:]
        if not path.endswith("/"):
            path = path + "/"
        s3_folders.add(path)

    generated_htmls = []
    s3_folders = sorted(s3_folders, key=FolderLenCompareKey)
    for folder_ in s3_folders:
        index_html = __generate_index_html(
            package_type, s3_client, bucket, folder_, top_level, prefix
        )
        if index_html:
            generated_htmls.append(index_html)

    root_index = __generate_index_html(
        package_type, s3_client, bucket, "/", top_level, prefix
    )
    if root_index:
        generated_htmls.append(root_index)

    return generated_htmls


def __generate_index_html(
    package_type: str,
    s3_client: S3Client,
    bucket: str,
    folder_: str,
    top_level: str,
    prefix: str = None
) -> str:
    if folder_ != "/":
        search_folder = os.path.join(prefix, folder_) if prefix else folder_
    else:
        search_folder = prefix if prefix else "/"
    contents = s3_client.list_folder_content(
        bucket_name=bucket,
        folder=search_folder
    )
    # Should filter out the .prodinfo files
    contents = [c for c in contents if not c.endswith(PROD_INFO_SUFFIX)]
    index = None
    if len(contents) == 1 and contents[0].endswith("index.html"):
        logger.info("The folder %s only contains index.html, "
                    "will remove it.", folder_)
        if folder_ == "/":
            removed_index = os.path.join(top_level, "index.html")
        else:
            removed_index = os.path.join(top_level, folder_, "index.html")
        s3_client.delete_files(
            file_paths=[removed_index],
            target=(bucket, prefix),
            product=None,
            root=top_level
        )
    elif len(contents) >= 1:
        real_contents = []
        if prefix and prefix.strip() != "":
            for c in contents:
                if c.startswith(prefix):
                    real_c = remove_prefix(c, prefix)
                    real_c = remove_prefix(real_c, "/")
                    real_contents.append(real_c)
                else:
                    real_contents.append(c)
        else:
            real_contents = contents
        index = __to_html(package_type, real_contents, folder_, top_level)

    return index


def __to_html(package_type: str, contents: List[str], folder: str, top_level: str) -> str:
    html_content = __to_html_content(package_type, contents, folder)
    html_path = os.path.join(top_level, folder, "index.html")
    if folder == "/":
        html_path = os.path.join(top_level, "index.html")
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, 'w', encoding='utf-8') as html:
        html.write(html_content)
    return html_path


def __to_html_content(package_type: str, contents: List[str], folder: str) -> str:
    items = []
    if folder != "/":
        items.append("../")
        for c in contents:
            # index.html does not need to be included in html content.
            if not c.endswith("index.html"):
                items.append(c[len(folder):])
    else:
        items.extend(contents)
    items = __sort_index_items(items)
    index = IndexedHTML(title=folder, header=folder, items=items)
    return index.generate_index_file_content(package_type)


def __sort_index_items(items):
    sorted_items = sorted(items, key=IndexedItemsCompareKey)
    # make sure metadata is the last element
    if 'maven-metadata.xml' in sorted_items:
        sorted_items.remove('maven-metadata.xml')
        sorted_items.append('maven-metadata.xml')
    return sorted_items


class FolderLenCompareKey:
    """Used as key function for folder sorting, will give DESC order
       based on the length of the parts splitted by slash of the folder
       path
    """

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        return self.__compare(other) < 0

    def __gt__(self, other):
        return self.__compare(other) > 0

    def __le__(self, other):
        return self.__compare(other) <= 0

    def __ge__(self, other):
        return self.__compare(other) >= 0

    def __eq__(self, other):
        return self.__compare(other) == 0

    def __hash__(self) -> int:
        return self.obj.__hash__()

    def __compare(self, other) -> int:
        xitems = self.obj.split("/")
        yitems = other.obj.split("/")
        return len(yitems) - len(xitems)


class IndexedItemsCompareKey:
    """Used as key function for indexed items sorting in index.html,
       will make all folder listed before files.
    """

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        return self.__compare(other) < 0

    def __gt__(self, other):
        return self.__compare(other) > 0

    def __le__(self, other):
        return self.__compare(other) <= 0

    def __ge__(self, other):
        return self.__compare(other) >= 0

    def __eq__(self, other):
        return self.__compare(other) == 0

    def __hash__(self) -> int:
        return self.obj.__hash__()

    def __compare(self, other) -> int:
        origin = self.obj
        target = other.obj
        if origin.endswith("/") and not target.endswith("/"):
            return -1
        if target.endswith("/") and not origin.endswith("/"):
            return 1
        if origin > target:
            return 1
        elif origin < target:
            return -1
        else:
            return 0


def re_index(
    bucket: Tuple[str, str, str, str, str],
    path: str,
    package_type: str,
    aws_profile: str = None,
    # cf_enable: bool = False,
    dry_run: bool = False
):
    """Refresh the index.html for the specified folder in the bucket.
    """
    bucket_name = bucket[1]
    prefix = bucket[2]
    s3_client = S3Client(aws_profile=aws_profile, dry_run=dry_run)
    real_prefix = prefix if prefix.strip() != "/" else ""
    s3_folder = os.path.join(real_prefix, path)
    if path.strip() == "" or path.strip() == "/":
        s3_folder = prefix
    items: List[str] = s3_client.list_folder_content(bucket_name, s3_folder)
    contents = [i for i in items if not i.endswith(PROD_INFO_SUFFIX)]
    if PACKAGE_TYPE_NPM == package_type:
        if any([True if "package.json" in c else False for c in contents]):
            logger.warning(
                "The path %s contains NPM package.json which will work as "
                "package metadata for indexing. This indexing is ignored.",
                path
            )
            return

    if len(contents) >= 1:
        real_contents = []
        if real_prefix and real_prefix.strip() != "":
            for c in contents:
                if c.strip() != "":
                    if c.startswith(real_prefix):
                        real_c = remove_prefix(c, real_prefix)
                        real_c = remove_prefix(real_c, "/")
                        real_contents.append(real_c)
                    else:
                        real_contents.append(c)
        else:
            real_contents = contents
        logger.debug(real_contents)
        index_content = __to_html_content(package_type, real_contents, path)
        if not dry_run:
            index_path = os.path.join(path, "index.html")
            if path == "/":
                index_path = "index.html"
            s3_client.simple_delete_file(index_path, (bucket_name, real_prefix))
            s3_client.simple_upload_file(
                index_path, index_content, (bucket_name, real_prefix),
                "text/html", digest_content(index_content)
            )
            # We will not invalidate index.html per cost consideration
            # if cf_enable:
            #     cf_client = CFClient(aws_profile=aws_profile)
            #     invalidate_cf_paths(cf_client, bucket, [index_path])
    else:
        logger.warning(
            "The path %s does not contain any contents in bucket %s. "
            "Will not do any re-indexing",
            path, bucket_name
        )
