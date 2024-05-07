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
from charon.pkgs.checksum_http import refresh_checksum
from charon.utils.files import (
    digest, HashType, get_hash_type
)
from tests.constants import INPUTS
from tests.base import PackageBaseTest
from tests.commons import TEST_BUCKET_2
from moto import mock_aws
from botocore.errorfactory import ClientError
from botocore.exceptions import HTTPClientError
import os
import tempfile
import shutil

CHECKSUMS = {
    ".md5": HashType.MD5,
    ".sha1": HashType.SHA1,
    ".sha256": HashType.SHA256,
    ".sha512": HashType.SHA512
}


@mock_aws
class ChecksumTest(PackageBaseTest):
    def setUp(self):
        super().setUp()
        self.target_ = (TEST_BUCKET_2, '')
        self.tmp_dir = tempfile.mkdtemp(prefix="charon-checksum-test-")
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET_2)
        self.test_bucket_2 = self.mock_s3.Bucket(TEST_BUCKET_2)

    def tearDown(self):
        buckets = [TEST_BUCKET_2]
        self.cleanBuckets(buckets)
        shutil.rmtree(self.tmp_dir)
        super().tearDown()

    def test_checksum_refresh_not_matched(self):
        fs = ["commons-client-4.5.6.zip", "commons-client-4.5.9.zip"]
        checksum_types = [".md5", ".sha1", ".sha256"]
        for f in fs:
            self.__upload_file(f)
            for hash_file_type in checksum_types:
                self.__upload_content(
                    f"wrong {hash_file_type}",
                    self.__get_test_key(f"{f}{hash_file_type}")
                )
        new_fs = [
            self.__get_test_key("commons-client-4.5.6.zip"),
            self.__get_test_key("commons-client-4.5.9.zip")
        ]
        refresh_checksum(self.target_, new_fs)
        for f_ in fs:
            for hash_file_type in checksum_types:
                f = self.__download_file(self.__get_test_key(f"{f_}{hash_file_type}"))
                self.assertTrue(os.path.exists(f))
                original_digest = self.__get_digest(f_, CHECKSUMS[hash_file_type])
                with open(f, "rb") as f:
                    updated_checksum = str(f.read(), encoding="utf-8")
                    self.assertEqual(original_digest, updated_checksum)
                for non_existed_hash_type in [".sha512"]:
                    self.assertFalse(
                        self.__check_file_exists(
                            self.__get_test_key(f"{f_}{non_existed_hash_type}")
                        )
                    )

    def test_checksum_refresh_already_matched(self):
        f_ = "commons-client-4.5.6.zip"
        self.__upload_file(f_)
        checksum_types = ["md5", "sha1"]
        for hash_file_type in checksum_types:
            hash_f = f"{f_}.{hash_file_type}"
            self.__upload_content(
                self.__get_digest(
                    f_,
                    get_hash_type(hash_file_type)
                ),
                self.__get_test_key(hash_f)
            )
        refresh_checksum(self.target_, [self.__get_test_key(f_)])
        f = self.__download_file(self.__get_test_key(f_))
        self.assertTrue(os.path.exists(f))
        for hash_file_type in checksum_types:
            type_key = f".{hash_file_type}"
            f = self.__download_file(self.__get_test_key(f"{f_}{type_key}"))
            self.assertTrue(os.path.exists(f))
            original_digest = self.__get_digest(f_, CHECKSUMS[type_key])
            with open(f, "rb") as f:
                updated_checksum = str(f.read(), encoding="utf-8")
                self.assertEqual(original_digest, updated_checksum)
            for non_existed_hash_type in [".sha256", ".sha512"]:
                self.assertFalse(
                    self.__check_file_exists(self.__get_test_key(f"{f_}{non_existed_hash_type}"))
                )

    def test_checksum_refresh_missing(self):
        f_ = "commons-client-4.5.6.zip"
        self.__upload_file(f_)
        key = self.__get_test_key(f_)
        refresh_checksum(self.target_, [key])
        f = self.__download_file(key)
        self.assertTrue(os.path.exists(f))
        for non_existed_hash_type in [".md5", ".sha1", ".sha256", ".sha512"]:
            self.assertFalse(
                self.__check_file_exists(self.__get_test_key(f"{f_}{non_existed_hash_type}"))
            )

    def __get_digest(self, file, hash_type):
        real_file = os.path.join(INPUTS, file)
        return digest(real_file, hash_type)

    def __get_test_key(self, file):
        return os.path.join("test", file)

    def __upload_file(self, file):
        real_file = os.path.join(INPUTS, file)
        self.test_bucket_2.put_object(
            Body=open(real_file, "rb"), Key=self.__get_test_key(file),
            ContentEncoding="utf-8"
        )

    def __upload_content(self, content, key):
        self.test_bucket_2.put_object(
            Body=content, Key=key,
            ContentEncoding="utf-8"
        )

    def __download_file(self, key) -> str:
        file_path = os.path.join(self.tmp_dir, key)
        folder_ = os.path.dirname(file_path)
        if not os.path.exists(folder_):
            os.makedirs(folder_)
        self.test_bucket_2.download_file(key, file_path)
        return file_path

    def __check_file_exists(self, key) -> bool:
        try:
            self.test_bucket_2.Object(key).load()
            return True
        except (ClientError, HTTPClientError) as e:
            if isinstance(e, ClientError) and e.response["Error"]["Code"] == "404":
                return False
            else:
                raise e
