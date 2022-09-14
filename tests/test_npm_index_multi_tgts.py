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
from charon.constants import PROD_INFO_SUFFIX, DEFAULT_REGISTRY
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from charon.storage import CHECKSUM_META_KEY
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, PackageBaseTest
from tests.commons import (
    TEST_BUCKET, CODE_FRAME_7_14_5_INDEXES,
    CODE_FRAME_7_15_8_INDEXES, COMMONS_ROOT_INDEX,
    TEST_BUCKET_2
)
from moto import mock_s3
import os

NAMESPACE_BABEL_INDEX = "@babel/index.html"


@mock_s3
class NpmFileIndexMultiTgtsTest(PackageBaseTest):
    def setUp(self):
        super().setUp()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET_2)
        self.test_bucket_2 = self.mock_s3.Bucket(TEST_BUCKET_2)

    def tearDown(self):
        buckets = [TEST_BUCKET_2]
        self.cleanBuckets(buckets)
        super().tearDown()

    def test_uploading_index(self):
        self.__test_upload_prefix()

    def test_uploding_index_with_short_prefix(self):
        self.__test_upload_prefix(SHORT_TEST_PREFIX)

    def test_uploding_index_with_long_prefix(self):
        self.__test_upload_prefix(LONG_TEST_PREFIX)

    def test_uploding_index_with_root_prefix(self):
        self.__test_upload_prefix("/")

    def __test_upload_prefix(self, prefix: str = None):
        targets_ = [(None, TEST_BUCKET, prefix, DEFAULT_REGISTRY),
                    (None, TEST_BUCKET_2, prefix, DEFAULT_REGISTRY)]
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=targets_,
            dir_=self.tempdir,
        )

        PREFIXED_7158_INDEXES = CODE_FRAME_7_15_8_INDEXES
        PREFIXED_NAMESPACE_BABEL_INDEX = NAMESPACE_BABEL_INDEX
        PREFIXED_ROOT_INDEX = COMMONS_ROOT_INDEX
        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]
            self.assertEqual(7, len(actual_files), msg=f'{bucket_name}')

            if prefix and prefix != "/":
                PREFIXED_7158_INDEXES = [
                    os.path.join(prefix, f) for f in CODE_FRAME_7_15_8_INDEXES
                ]
                PREFIXED_NAMESPACE_BABEL_INDEX = os.path.join(prefix, NAMESPACE_BABEL_INDEX)
                PREFIXED_ROOT_INDEX = os.path.join(prefix, COMMONS_ROOT_INDEX)

            for assert_file in PREFIXED_7158_INDEXES:
                self.assertNotIn(assert_file, actual_files, msg=f'{bucket_name}')

            for obj in objs:
                if not obj.key.endswith(PROD_INFO_SUFFIX):
                    self.assertIn(
                        CHECKSUM_META_KEY, obj.Object().metadata, msg=f'{bucket_name}'
                    )
                    self.assertNotEqual(
                        "", obj.Object().metadata[CHECKSUM_META_KEY].strip(), msg=f'{bucket_name}'
                    )

            indedx_obj = bucket.Object(PREFIXED_NAMESPACE_BABEL_INDEX)
            index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<a href=\"code-frame/\" title=\"code-frame/\">code-frame/</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertIn(
                "<a href=\"../index.html\" title=\"../\">../</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertNotIn(PROD_INFO_SUFFIX, index_content, msg=f'{bucket_name}')

            indedx_obj = bucket.Object(PREFIXED_ROOT_INDEX)
            index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<a href=\"@babel/index.html\" title=\"@babel/\">@babel/</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertNotIn(
                "<a href=\"../index.html\" title=\"../\">../</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertNotIn(PROD_INFO_SUFFIX, index_content, msg=f'{bucket_name}')

    def test_overlap_upload_index(self):
        self.__prepare_content()
        targets_ = [(None, TEST_BUCKET, None), (None, TEST_BUCKET_2, None)]
        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]
            self.assertEqual(11, len(objs), msg=f'{bucket_name}')

            self.assertIn(
                NAMESPACE_BABEL_INDEX, actual_files, msg=f'{bucket_name}'
            )
            for assert_file in CODE_FRAME_7_14_5_INDEXES:
                self.assertNotIn(assert_file, actual_files, msg=f'{bucket_name}')
            for assert_file in CODE_FRAME_7_15_8_INDEXES:
                self.assertNotIn(assert_file, actual_files, msg=f'{bucket_name}')

            indedx_obj = bucket.Object(NAMESPACE_BABEL_INDEX)
            index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<a href=\"code-frame/\" title=\"code-frame/\">code-frame/</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertIn(
                "<a href=\"../index.html\" title=\"../\">../</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertNotIn(
                PROD_INFO_SUFFIX, index_content, msg=f'{bucket_name}'
            )

    def test_deletion_index(self):
        self.__test_deletion_prefix()

    def test_deletion_index_with_short_prefix(self):
        self.__test_deletion_prefix(SHORT_TEST_PREFIX)

    def test_deletion_index_with_long_prefix(self):
        self.__test_deletion_prefix(LONG_TEST_PREFIX)

    def test_deletion_index_with_root_prefix(self):
        self.__test_deletion_prefix("/")

    def __test_deletion_prefix(self, prefix: str = None):
        self.__prepare_content(prefix)
        targets_ = [(None, TEST_BUCKET, prefix, None), (None, TEST_BUCKET_2, prefix, None)]
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5,
            buckets=targets_,
            dir_=self.tempdir
        )

        PREFIXED_NAMESPACE_BABEL_INDEX = NAMESPACE_BABEL_INDEX
        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]
            self.assertEqual(7, len(objs), msg=f'{bucket_name}')

            if prefix and prefix != "/":
                PREFIXED_NAMESPACE_BABEL_INDEX = os.path.join(prefix, NAMESPACE_BABEL_INDEX)

            self.assertIn(PREFIXED_NAMESPACE_BABEL_INDEX, actual_files, msg=f'{bucket_name}')

            for obj in objs:
                if not obj.key.endswith(PROD_INFO_SUFFIX):
                    self.assertIn(
                        CHECKSUM_META_KEY, obj.Object().metadata, msg=f'{bucket_name}'
                    )
                    self.assertNotEqual(
                        "", obj.Object().metadata[CHECKSUM_META_KEY].strip(), msg=f'{bucket_name}'
                    )

            indedx_obj = bucket.Object(PREFIXED_NAMESPACE_BABEL_INDEX)
            index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<a href=\"code-frame/\" title=\"code-frame/\">code-frame/</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertIn(
                "<a href=\"../index.html\" title=\"../\">../</a>",
                index_content, msg=f'{bucket_name}'
            )
            self.assertNotIn(PROD_INFO_SUFFIX, index_content, msg=f'{bucket_name}')

        product_7_15_8 = "code-frame-7.15.8"
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        handle_npm_del(
            test_tgz, product_7_15_8,
            buckets=targets_,
            dir_=self.tempdir
        )

        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            self.assertEqual(0, len(objs), msg=f'{bucket_name}')

    def __prepare_content(self, prefix: str = None):
        targets_ = [(None, TEST_BUCKET, prefix, DEFAULT_REGISTRY),
                    (None, TEST_BUCKET_2, prefix, DEFAULT_REGISTRY)]
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=targets_,
            dir_=self.tempdir
        )

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8,
            buckets=targets_,
            dir_=self.tempdir
        )
