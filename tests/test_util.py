
import os
import unittest
from mrrc.util import digest,read_sha1, HashType

class UtilTest(unittest.TestCase):
    def test_digest(self):
        test_file = os.path.join(os.getcwd(),"tests-input/commons-lang3.zip")
        self.assertEqual("1911950fd8ab289c6d19f0ba74574e92",digest(test_file,HashType.MD5))
        self.assertEqual("841a09c5820f6956461cd07afdbf5c25d3cb9b26",digest(test_file))
        self.assertEqual("dc04f0b04f4aba4211a98e6555ec906c3de3a362f668a874bb4783a30e4cdc7c", digest(test_file,HashType.SHA256))
        
    def test_read_sha1(self):
        test_file = os.path.join(os.getcwd(),"tests-input/commons-lang3.zip")
        # read the real sha1 hash
        self.assertEqual("841a09c5820f6956461cd07afdbf5c25d3cb9b26",digest(test_file))
        # read hash from .sha1 file
        self.assertEqual("841a09c5820f6956461cd07afdbf5c25d3cb9c26",read_sha1(test_file))
        
        # For .sha1 file itself, will use digest directly
        test_file = os.path.join(os.getcwd(),"tests-input/commons-lang3.zip.sha1")
        self.assertEqual(digest(test_file), read_sha1(test_file))