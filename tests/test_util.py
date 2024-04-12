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
from charon.utils.files import digest, digest_content, read_sha1, HashType
import os
import unittest

from tests.constants import INPUTS


class UtilTest(unittest.TestCase):
    def test_digest(self):
        test_file = os.path.join(INPUTS, "commons-lang3.zip")
        self.assertEqual("bd4fe0a8111df64430b6b419a91e4218ddf44734", digest(test_file))
        self.assertEqual(
            "61ff1d38cfeb281b05fcd6b9a2318ed47cd62c7f99b8a9d3e819591c03fe6804",
            digest(test_file, HashType.SHA256),
        )

    def test_digest_content(self):
        test_content = "test common content"
        self.assertEqual("8c7b70f25fb88bc6a0372f70f6805132e90e2029", digest_content(test_content))
        self.assertEqual(
            "1a1c26da1f6830614ed0388bb30d9e849e05bba5de4031e2a2fa6b48032f5354",
            digest_content(test_content, HashType.SHA256),
        )

    def test_read_sha1(self):
        test_file = os.path.join(INPUTS, "commons-lang3.zip")
        # read the real sha1 hash
        self.assertEqual("bd4fe0a8111df64430b6b419a91e4218ddf44734", digest(test_file))
        # read hash from .sha1 file
        self.assertEqual(
            "bd4fe0a8111df64430b6b419a91e4218ddf44734", read_sha1(test_file)
        )

        # For .sha1 file itself, will use digest directly
        test_file = os.path.join(INPUTS, "commons-lang3.zip.sha1")
        self.assertEqual(digest(test_file), read_sha1(test_file))
