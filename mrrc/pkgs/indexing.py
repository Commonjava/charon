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
from mrrc.storage import S3Client
from jinja2 import Template
from treelib import Tree, Node
import uuid
import os
from typing import List
from lxml.html import fromstring


class IndexHTML(object):
    # object for holding index html file data
    def __init__(self, title: str, header: str, items: List[str]):
        self.title = title
        self.header = header
        self.items = items

    def generate_index_file_content(self) -> str:
        template = Template(get_index_template())
        return template.render(index=self)


def get_index_template() -> str:
    DEFAULT_INDEX_TEMPLATE = os.path.join(
        os.environ["HOME"], ".mrrc/template/index.html.j2"
    )
    with open(DEFAULT_INDEX_TEMPLATE, encoding="utf-8") as file_:
        return file_.read()


def path_to_index(top_level: str, valid_paths: List[str], bucket: str):
    repos = []
    for path in valid_paths:
        if path.startswith(top_level):
            store_path = path.replace(top_level, '')
            if store_path[0] == '/':
                store_path = store_path[1:]
            repos.append(store_path)

    tree = tree_convert(repos)
    index_files = html_convert(tree, '/', top_level, bucket)
    return index_files


def tree_convert(output):
    tree = Tree()
    temp_node = Node(identifier='root', tag="/", data="/")
    tree.add_node(temp_node)

    # example of line: net/java/jvnet-parent/4.0.0.redhat-3/jvnet-parent-4.0.0.redhat-3.pom
    for line in output:
        paths = line.split('/')

        paths = [p + '/' for p in paths[:-1]] + [paths[-1]]

        id_holder = 'root'
        for path in paths:
            for child in tree.is_branch(id_holder):
                if tree[child].tag == path:
                    id_holder = child
                    break
            else:
                temp_node = Node(identifier=uuid.uuid4(), tag=path, data=path)
                tree.add_node(temp_node, parent=id_holder)
                id_holder = temp_node.identifier
                continue

    return tree


def html_convert(tree: Tree, path: str, base_dir: str, bucket: str):
    # items that needs to be display, e.g org/
    items = []

    html_files = []

    for child in tree.is_branch(tree.root):
        # if there is no child, rest of the codes won't be executed
        if tree[child].tag != '/index.html':
            items.append(tree[child].tag)
        else:
            continue

        html_files = html_files + html_convert(tree.subtree(tree[child].identifier),
                                               os.path.join(path, tree[child].tag),
                                               base_dir, bucket)
        # items should be filled by here

    # input tree is already deduplicated so this will not generate duplicated index.html
    if tree.is_branch(tree.root) != []:
        target = os.path.join(base_dir + path + 'index.html')

        if path != '/':
            items.append('../')

        print(path)
        items += set(load_exist_index(bucket, os.path.join(path, 'index.html')[1:]))

        index = IndexHTML(title=path, header=path, items=items)
        # this path can be modified if we want to store them somewhere else
        html_files.append(target)
        with open(target, 'w') as index_file:
            index_file.write(index.generate_index_file_content())

    return html_files


def load_exist_index(bucket: str, path: str) -> List[str]:
    items = []

    s3_client = S3Client()
    try:
        content = s3_client.read_file_content(bucket_name=bucket, key=path)
        content = content.replace('\n', '').replace('\t', '')
        print(content)
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            return []
        else:
            raise
    root = fromstring(content)
    for item in root.iter('a'):
        items.append(item.attrib.get('title'))

    return items
