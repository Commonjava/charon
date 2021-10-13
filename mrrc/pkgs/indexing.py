from jinja2 import Template
from treelib import Tree, Node
import uuid
import os
from typing import List
# import xml.etree.ElementTree as ET


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


def path_to_index(top_level: str, valid_paths: List[str]):
    repos = []
    for path in valid_paths:
        if path.startswith(top_level):
            repos.append(path.replace(top_level + '/', ''))

    tree = tree_convert(repos)
    index_files = html_convert(tree, '/', top_level)
    return index_files


def tree_convert(output):
    tree = Tree()
    temp_node = Node(identifier='root', tag="/", data="/")
    tree.add_node(temp_node)

    # example of line: net/java/jvnet-parent/4.0.0.redhat-3/jvnet-parent-4.0.0.redhat-3.pom
    for line in output:
        paths = line.split('/')

        id_holder = 'root'
        for path in paths:
            for child in tree.is_branch(id_holder):
                if tree[child].tag == path:
                    id_holder = child
                    break
            else:
                store_path = path
                if path != paths[:-1]:
                    store_path += '/'
                temp_node = Node(identifier=uuid.uuid4(), tag=store_path, data=path)
                tree.add_node(temp_node, parent=id_holder)
                id_holder = temp_node.identifier
                continue

    return tree


def html_convert(tree: Tree, path: str, base_dir: str):
    # items that needs to be display, e.g org/
    items = []

    html_files = []

    for child in tree.is_branch(tree.root):
        # if there is no child, rest of the codes won't be executed
        if tree[child].tag != 'index.html':
            items.append(tree[child].tag)
        else:
            continue

        html_files = html_files + html_convert(tree.subtree(tree[child].identifier),
                                               os.path.join(path, tree[child].tag), base_dir)
        # items should be filled by here

    # input tree is already deduplicated so this will not generate duplicated index.html
    if tree.is_branch(tree.root) != []:
        target = base_dir + path + '/index.html'

        if path != '/':
            items.append('../')
        else:
            target = target.replace('//', '/')

        index = IndexHTML(title=path, header=path, items=items)
        # this path can be modified if we want to store them somewhere else
        html_files.append(target)
        with open(target, 'w') as index_file:
            index_file.write(index.generate_index_file_content())

    return html_files
