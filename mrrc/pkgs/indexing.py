"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

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
from botocore.exceptions import ClientError
from mrrc.config import get_template
from mrrc.storage import S3Client
from jinja2 import Template
import os
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class IndexedHTML(object):
    # object for holding index html file data
    def __init__(self, title: str, header: str, items: Set[str]):
        self.title = title
        self.header = header
        self.items = items

    def generate_index_file_content(self) -> str:
        template = Template(get_index_template())
        return template.render(index=self)


def get_index_template() -> str:
    return get_template("index.html.j2")


def handle_create_index(
    top_level: str, uploaded_files: List[str], s3_client: S3Client, bucket: str
):
    if top_level[-1] != '/':
        top_level += '/'

    repos, updated_indexes, temp_dirs = set(), set(), set()

    # chopp down every lines, left s3 client key format
    for path in uploaded_files:
        path = path.replace(top_level, '')
        repos.add(path)
    for repo in repos:
        repo_index = os.path.join(top_level, os.path.dirname(repo), '.index')
        os.makedirs(os.path.dirname(repo_index), exist_ok=True)
        with open(repo_index, 'a+', encoding='utf-8') as f:
            f.write(os.path.basename(repo) + '\n')
        updated_indexes.add(os.path.join(os.path.dirname(repo), '.index'))

    # updated_indexes containes only objects not in s3, record them on disk
    for index in updated_indexes:
        items = load_s3_index(s3_client, bucket, index)
        if items != set():
            with open(os.path.join(top_level, index), 'a+', encoding='utf-8') as f:
                _items = set(_.replace('\n', '') for _ in f.readlines())
                for item in items.difference(_items):
                    f.write(item + '\n')
        else:
            temp_dirs.add(os.path.dirname(index))

    # the function will also merge indexes on disk
    for temp_dir in temp_dirs:
        virtual_folder_create(temp_dir, top_level, s3_client, bucket, updated_indexes)

    updated_indexes = {os.path.join(top_level, _) for _ in updated_indexes}
    html_files = index_to_html(updated_indexes, top_level)
    return updated_indexes.union(html_files)


def handle_delete_index(
    top_level: str, deleted_files: List[str], s3_client: S3Client, bucket: str
):
    if top_level[-1] != '/':
        top_level += '/'

    repos, delete_indexes, updated_indexes, temp_dirs = set(), set(), set(), set()

    for path in deleted_files:
        path = path.replace(top_level, '')
        repos.add(path)
    for repo in repos:
        repo_index = os.path.join(top_level, os.path.dirname(repo), '.index')
        os.makedirs(os.path.dirname(repo_index), exist_ok=True)
        with open(repo_index, 'a+', encoding='utf-8') as f:
            f.write(os.path.basename(repo) + '\n')
        updated_indexes.add(os.path.join(os.path.dirname(repo), '.index'))

    # It's certain the index is not placed locally, load them from s3
    for index in set(updated_indexes):
        items = load_s3_index(s3_client, bucket, index)
        with open(os.path.join(top_level, index), 'r+', encoding='utf-8') as f:
            _items = set(_.replace('\n', '') for _ in f.readlines())
            left_items = items.difference(_items)
            if left_items != set():
                # cleans everthing locally
                f.seek(0)
                f.truncate()
                for item in left_items:
                    f.write(item + '\n')
            else:
                temp_dirs.add(os.path.dirname(index))
                updated_indexes.remove(index)
                delete_indexes.add(index)

    for temp_dir in temp_dirs:
        virtual_folder_delete(temp_dir, top_level, s3_client, bucket,
                              updated_indexes, delete_indexes)

    html_files = set()
    if updated_indexes != set():
        updated_indexes = {os.path.join(top_level, _) for _ in updated_indexes}
        html_files = index_to_html(updated_indexes, top_level)
    if delete_indexes != set():
        for index in set(delete_indexes):
            delete_indexes.add(os.path.join(os.path.dirname(index), 'index.html'))
    return delete_indexes, updated_indexes.union(html_files)


# e.g path: org/apache/httpcomponents/httpclient/4.5.6, updated_indexes contains every local index
def virtual_folder_create(
    path: str, base_dir: str, s3_client: S3Client, bucket: str, updated_indexes: Set[str]
):
    item = os.path.basename(path) + '/'
    dir_index = os.path.join(os.path.dirname(path), '.index')
    local_index_file = os.path.join(base_dir, dir_index)
    updated_indexes.add(dir_index)
    rec_flag = False

    # first load from disk to see if .index file exists that should contain current path
    if os.path.exists(local_index_file):
        items = load_local_index(local_index_file)
        if item in items:
            return
        else:
            # only appends line, no truncate and no overwrite
            with open(local_index_file, 'a', encoding='utf-8') as f:
                f.write(item + '\n')
    else:
        # if the .index file does not exist on local, try load it from s3
        items = load_s3_index(s3_client, bucket, dir_index)
        # items will be empty if the s3 does not contain this .index file
        if items == set():
            with open(local_index_file, 'a+', encoding='utf-8') as f:
                f.write(item + '\n')
                rec_flag = True
        # if we load something from s3, that means the upper folder is present on their .index file
        # then write everthing to local disk and our path as well
        else:
            with open(local_index_file, 'a+', encoding='utf-8') as f:
                for _ in items:
                    f.write(_ + '\n')
                if item not in items:
                    f.write(item + '\n')
        # when this is not root '.index' file, pass the upper folder to recursive
        # this creates it's upper folder
        if rec_flag and dir_index != '.index':
            virtual_folder_create(os.path.dirname(path), base_dir, s3_client, bucket,
                                  updated_indexes)

    return


def virtual_folder_delete(
    path: str, base_dir: str, s3_client: S3Client, bucket: str,
    updated_indexes: Set[str], delete_indexes: Set[str]
):
    item = os.path.basename(path) + '/'
    dir_index = os.path.join(os.path.dirname(path), '.index')
    local_index_file = os.path.join(base_dir, dir_index)
    updated_indexes.add(dir_index)
    rec_flag = False

    if os.path.exists(local_index_file):
        with open(local_index_file, 'r+', encoding='utf-8') as f:
            items = set(_.replace('\n', '') for _ in f.readlines())
            if items == set():
                return
            letf_items = items.difference({item})
            if letf_items == set():
                updated_indexes.remove(dir_index)
                delete_indexes.add(dir_index)
                rec_flag = True
            else:
                f.seek(0)
                f.truncate()
                for i in letf_items:
                    f.write(i + '\n')
    else:
        items = load_s3_index(s3_client, bucket, dir_index)
        with open(local_index_file, 'w+', encoding='utf-8') as f:
            letf_items = items.difference({item})
            if letf_items == set():
                updated_indexes.remove(dir_index)
                delete_indexes.add(dir_index)
                rec_flag = True
            else:
                for i in letf_items:
                    f.write(i + '\n')

    if rec_flag and dir_index != '.index':
        virtual_folder_delete(os.path.dirname(path), base_dir, s3_client, bucket,
                              updated_indexes, delete_indexes)

    return


def index_to_html(items_files: Set[str], base_dir: str):
    html_files = []
    for file in items_files:
        with open(file, 'r', encoding='utf-8') as f:
            items = set(_.replace('\n', '') for _ in f.readlines())
        if file != os.path.join(base_dir, '.index'):
            path = os.path.dirname(file).replace(base_dir, '')
            html_location = os.path.join(os.path.dirname(file), 'index.html')
            items.add('../')
        else:
            path = '/'
            html_location = os.path.join(base_dir, 'index.html')
        items = sort_index_items(items)
        html_files.append(html_location)
        index = IndexedHTML(title=path, header=path, items=items)
        with open(os.path.join(base_dir, html_location), 'w', encoding='utf-8') as index_html_file:
            index_html_file.write(index.generate_index_file_content())
    return html_files


def load_s3_index(s3_client: S3Client, bucket: str, path: str) -> Set[str]:
    try:
        content = s3_client.read_file_content(bucket_name=bucket, key=path)
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            return set()
        else:
            raise

    stored_items = set(content.split('\n')[:-1])
    return stored_items


def load_local_index(local_index_file: str) -> Set[str]:
    if os.path.exists(local_index_file):
        with open(local_index_file, 'r', encoding='utf-8') as f:
            items = set(_.replace('\n', '') for _ in f.readlines())
        return items
    else:
        return set()


def sort_index_items(items):
    sorted_items = sorted(items)
    # make sure metadata is the last element
    if 'maven-metadata.xml' in sorted_items:
        sorted_items.remove('maven-metadata.xml')
        sorted_items.append('maven-metadata.xml')
    elif 'package.json' in sorted_items:
        sorted_items.remove('package.json')
        sorted_items.append('package.json')

    return sorted_items
