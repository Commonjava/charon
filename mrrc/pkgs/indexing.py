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
from treelib import Tree, Node
import uuid
import os
from typing import List, Set


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


def path_to_index(top_level: str, valid_paths: List[str], bucket: str):
    repos = []
    for path in valid_paths:
        if path.startswith(top_level):
            path = path.replace(top_level, '')
            if path[0] == '/':
                path = path[1:]
            repos.append(path)

    tree = tree_convert(repos)
    index_files = html_convert(tree, '/', top_level, bucket)
    return index_files


def tree_convert(paths) -> Tree:
    tree = Tree()
    temp_node = Node(identifier='root', tag="/", data="/")
    tree.add_node(temp_node)

    # example of line: net/java/jvnet-parent/4.0.0.redhat-3/jvnet-parent-4.0.0.redhat-3.pom
    for path in paths:
        # escaped '/' could break logic here, improve in the future
        items = path.split('/')
        items = [p + '/' for p in items[:-1]] + [items[-1]]

        id_holder = 'root'
        for item in items:
            for child in tree.is_branch(id_holder):
                if tree[child].tag == item:
                    id_holder = child
                    break
            else:
                temp_node = Node(identifier=uuid.uuid4(), tag=item, data=item)
                tree.add_node(temp_node, parent=id_holder)
                id_holder = temp_node.identifier
                # continue

    return tree


def get_update_list(repos: List[str], top_level: str, bucket: str):

    base_dir = top_level
    if not top_level.endswith('/'):
        base_dir += '/'
    _repos = set(_.replace(base_dir, '') for _ in repos)
    (deleted_files, delete_index, update_index) = update_items(_repos, [], [], base_dir, bucket)
    while deleted_files != set():
        (deleted_files, delete_index, update_index) = update_items(deleted_files, delete_index,
                                                                   update_index, base_dir, bucket)
    # Generate index.html file from every .index file
    for file in list(update_index):
        with open(file, 'r', encoding='utf-8') as f:
            items = set(_.replace('\n', '') for _ in f.readlines())
        if file != os.path.join(base_dir, '.index'):
            path = os.path.join(*file.replace(base_dir, '').split('/')[:-1])
            html_location = os.path.join(base_dir, path, 'index.html')
            items.add('../')
        else:
            path = '/'
            html_location = os.path.join(base_dir, 'index.html')
        index = IndexedHTML(title=path, header=path, items=items)
        update_index.append(html_location)
        with open(os.path.join(base_dir, html_location), 'w', encoding='utf-8') as index_html_file:
            index_html_file.write(index.generate_index_file_content())
    # Add index.html for deletion
    for file in list(delete_index):
        delete_index.append(file.replace('.index', 'index.html'))

    return (delete_index, update_index)


def update_items(deleted_files: Set[str], delete_index: List[str],
                 update_index: List[str], base_dir: str, bucket: str):

    scanned = set()
    _deleted_files = set(deleted_files)

    for d_file in _deleted_files:
        if d_file in scanned:
            continue
        if len(d_file.split('/')[:-1]) != 0:
            path = os.path.join(*d_file.split('/')[:-1])
        else:
            path = ''

        index_file = os.path.join(path, '.index')
        local_index_file = os.path.join(base_dir, index_file)

        items = []
        # if we already updated it, we need read from local to get what item left there
        if local_index_file in update_index:
            with open(local_index_file, 'r', encoding='utf-8') as f:
                items = set(_.replace('\n', '') for _ in f.readlines())
        else:
            items = load_exist_index(bucket, index_file)

        # scan list to find items in same folder, and remove them from .index file
        for _ in set(deleted_files):
            if _ in scanned:
                continue
            if _.startswith(path) and path != '':
                if _.split('/')[-1] in items:
                    items.remove(_.split('/')[-1])
                    scanned.add(_)
                    deleted_files.remove(_)
                elif _.split('/')[-1]+'/' in items:
                    items.remove(_.split('/')[-1] + '/')
                    scanned.add(_)
                    deleted_files.remove(_)

        if path == '' and (d_file in items or d_file + '/' in items):
            if d_file in items:
                items.remove(d_file)
            elif d_file + '/' in items:
                items.remove(d_file + '/')
            deleted_files.remove(d_file)

        # if every item has been removed from list, it means the upperlevel folder is empty
        # thus add it to removed files to scann its upper level
        if items == set():
            delete_index.append(local_index_file)
            if path != '':
                deleted_files.add(path)
            if local_index_file in update_index:
                update_index.remove(local_index_file)
        # if there is still items left, save it on local file, and mark it has already been updated
        else:
            items_location = local_index_file
            update_index.append(items_location)
            with open(items_location, 'w', encoding='utf-8') as _file:
                for item in items:
                    _file.write(str(item) + '\n')

    for d_file in _deleted_files:
        if d_file in deleted_files:
            # if a line is still in the files, it's nowhere to be found in .index. delete it
            deleted_files.remove(d_file)

    return (deleted_files, delete_index, update_index)


def html_convert(tree: Tree, path: str, base_dir: str, bucket: str):
    # items that needs to be display, e.g org/
    items, html_files, items_files = set(), [], []

    for child in tree.is_branch(tree.root):
        # if there is no child, rest of the codes won't be executed
        if tree[child].tag != '/index.html':
            items.add(tree[child].tag)
        else:
            continue

        html_files = html_files + html_convert(tree.subtree(tree[child].identifier),
                                               os.path.join(path, tree[child].tag),
                                               base_dir, bucket)
        # items should be filled by here

    # input tree is already deduplicated so this will not generate duplicated index.html
    if tree.is_branch(tree.root) != []:
        # eliminats first '/' in path; if path is just /, it will be ''.
        html_location = os.path.join(base_dir, path[1:], 'index.html')
        items_location = os.path.join(base_dir, path[1:], '.index')

        items = items.union(load_exist_index(bucket, os.path.join(path, '.index')[1:]))

        items_files.append(items_location)
        with open(items_location, 'w', encoding='utf-8') as index_file:
            for item in items:
                index_file.write(str(item) + '\n')

        # adds option to get back to upper layer except for root, will not stored in .index
        if path != '/':
            items.add('../')

        index = IndexedHTML(title=path, header=path, items=items)
        # this path can be modified if we want to store them somewhere else
        html_files.append(html_location)
        with open(html_location, 'w', encoding='utf-8') as index_html_file:
            index_html_file.write(index.generate_index_file_content())

    return html_files + items_files


def load_exist_index(bucket: str, path: str) -> Set[str]:
    s3_client = S3Client()
    try:
        content = s3_client.read_file_content(bucket_name=bucket, key=path)
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            return []
        else:
            raise

    stored_items = set(content.split('\n')[:-1])
    return stored_items
