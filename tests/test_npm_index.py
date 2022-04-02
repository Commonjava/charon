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
    CODE_FRAME_7_15_8_INDEXES, COMMONS_ROOT_INDEX
)
from moto import mock_s3
import os

NAMESPACE_BABEL_INDEX = "@babel/index.html"


@mock_s3
class NpmFileIndexTest(PackageBaseTest):
    def test_uploading_index(self):
        self.__test_upload_prefix()

    def test_uploding_index_with_short_prefix(self):
        self.__test_upload_prefix(SHORT_TEST_PREFIX)

    def test_uploding_index_with_long_prefix(self):
        self.__test_upload_prefix(LONG_TEST_PREFIX)

    def test_uploding_index_with_root_prefix(self):
        self.__test_upload_prefix("/")

    def __test_upload_prefix(self, prefix: str = None):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[(None, TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
            dir_=self.tempdir,
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(7, len(actual_files))

        PREFIXED_7158_INDEXES = CODE_FRAME_7_15_8_INDEXES
        PREFIXED_NAMESPACE_BABEL_INDEX = NAMESPACE_BABEL_INDEX
        PREFIXED_ROOT_INDEX = COMMONS_ROOT_INDEX
        if prefix and prefix != "/":
            PREFIXED_7158_INDEXES = [
                os.path.join(prefix, f) for f in CODE_FRAME_7_15_8_INDEXES
            ]
            PREFIXED_NAMESPACE_BABEL_INDEX = os.path.join(prefix, NAMESPACE_BABEL_INDEX)
            PREFIXED_ROOT_INDEX = os.path.join(prefix, COMMONS_ROOT_INDEX)

        for assert_file in PREFIXED_7158_INDEXES:
            self.assertNotIn(assert_file, actual_files)

        for obj in objs:
            if not obj.key.endswith(PROD_INFO_SUFFIX):
                self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
                self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(PREFIXED_NAMESPACE_BABEL_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"code-frame/\" title=\"code-frame/\">code-frame/</a>",
                      index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)
        self.assertNotIn(PROD_INFO_SUFFIX, index_content)

        indedx_obj = test_bucket.Object(PREFIXED_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"@babel/index.html\" title=\"@babel/\">@babel/</a>", index_content)
        self.assertNotIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)
        self.assertNotIn(PROD_INFO_SUFFIX, index_content)

    def test_overlap_upload_index(self):
        self.__prepare_content()

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(11, len(objs))

        self.assertIn(NAMESPACE_BABEL_INDEX, actual_files)
        for assert_file in CODE_FRAME_7_14_5_INDEXES:
            self.assertNotIn(assert_file, actual_files)
        for assert_file in CODE_FRAME_7_15_8_INDEXES:
            self.assertNotIn(assert_file, actual_files)

        indedx_obj = test_bucket.Object(NAMESPACE_BABEL_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"code-frame/\" title=\"code-frame/\">code-frame/</a>",
                      index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)
        self.assertNotIn(PROD_INFO_SUFFIX, index_content)

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

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5,
            targets=[(None, TEST_BUCKET, prefix, None)],
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(7, len(objs))

        PREFIXED_NAMESPACE_BABEL_INDEX = NAMESPACE_BABEL_INDEX
        if prefix and prefix != "/":
            PREFIXED_NAMESPACE_BABEL_INDEX = os.path.join(prefix, NAMESPACE_BABEL_INDEX)

        self.assertIn(PREFIXED_NAMESPACE_BABEL_INDEX, actual_files)

        for obj in objs:
            if not obj.key.endswith(PROD_INFO_SUFFIX):
                self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
                self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(PREFIXED_NAMESPACE_BABEL_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"code-frame/\" title=\"code-frame/\">code-frame/</a>",
                      index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)
        self.assertNotIn(PROD_INFO_SUFFIX, index_content)

        product_7_15_8 = "code-frame-7.15.8"
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        handle_npm_del(
            test_tgz, product_7_15_8,
            targets=[(None, TEST_BUCKET, prefix, None)],
            dir_=self.tempdir
        )

        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def __prepare_content(self, prefix: str = None):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[(None, TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
            dir_=self.tempdir
        )

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8,
            targets=[(None, TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
            dir_=self.tempdir
        )
