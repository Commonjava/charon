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
import os
import unittest

from mrrc.utils.files import digest, read_sha1, HashType


class UtilTest(unittest.TestCase):
    def test_digest(self):
        test_file = os.path.join(os.getcwd(), "tests/input/commons-lang3.zip")
        self.assertEqual("1911950fd8ab289c6d19f0ba74574e92", digest(test_file, HashType.MD5))
        self.assertEqual("841a09c5820f6956461cd07afdbf5c25d3cb9b26", digest(test_file))
        self.assertEqual("dc04f0b04f4aba4211a98e6555ec906c3de3a362f668a874bb4783a30e4cdc7c",
                         digest(test_file, HashType.SHA256))

    def test_read_sha1(self):
        test_file = os.path.join(os.getcwd(), "tests/input/commons-lang3.zip")
        # read the real sha1 hash
        self.assertEqual("841a09c5820f6956461cd07afdbf5c25d3cb9b26", digest(test_file))
        # read hash from .sha1 file
        self.assertEqual("841a09c5820f6956461cd07afdbf5c25d3cb9c26", read_sha1(test_file))

        # For .sha1 file itself, will use digest directly
        test_file = os.path.join(os.getcwd(), "tests/input/commons-lang3.zip.sha1")
        self.assertEqual(digest(test_file), read_sha1(test_file))
