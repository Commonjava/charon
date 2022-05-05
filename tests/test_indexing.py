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

from charon.pkgs.indexing import FolderLenCompareKey, IndexedItemsCompareKey
from tests.base import BaseTest


class IndexingTest(BaseTest):
    def test_folder_len_compare(self):
        comp_class = FolderLenCompareKey
        self.assertGreater(comp_class("org"), comp_class("org/apache"))
        self.assertGreater(comp_class("org/"), comp_class("org/apache/"))
        self.assertLess(comp_class("org/commons"), comp_class("org"))
        self.assertEqual(comp_class("org/"), comp_class("org/"))
        self.assertEqual(comp_class("org"), comp_class("commons-io"))
        self.assertEqual(comp_class("com/redhat"), comp_class("org/commons"))

    def test_index_items_compare(self):
        comp_class = IndexedItemsCompareKey
        self.assertLess(comp_class("apache"), comp_class("beacon"))
        self.assertGreater(comp_class("apache"), comp_class("beacon/"))
        self.assertEqual(comp_class("apache"), comp_class("apache"))
        self.assertEqual(comp_class("apache/"), comp_class("apache/"))
        self.assertLess(comp_class("apache/"), comp_class("apache"))
        self.assertLess(comp_class("apache/"), comp_class("readme.md"))
        self.assertLess(comp_class("apache/"), comp_class("commons-io/"))
