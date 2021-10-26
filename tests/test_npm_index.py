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
from mrrc.pkgs.npm import handle_npm_uploading, handle_npm_del
from mrrc.storage import CHECKSUM_META_KEY
from tests.base import BaseMRRCTest
from moto import mock_s3
import boto3
import os

TEST_BUCKET = "test_bucket"

TEST_BUCKET = "npm_bucket"

CODE_FRAME_7_14_5_INDEXES = [
    "@babel/code-frame/7.14.5/index.html",
    "@babel/code-frame/-/index.html",
    "@babel/index.html"
]

CODE_FRAME_7_15_8_INDEXES = [
    "@babel/code-frame/7.15.8/index.html",
    "@babel/code-frame/-/index.html",
    "@babel/index.html"
]

CODE_FRAME_7_14_5_INDEX = "@babel/code-frame/7.14.5/index.html"

CODE_FRAME_INDEX = "@babel/code-frame/index.html"

COMMONS_ROOT_INDEX = "index.html"


@mock_s3
class NpmFileIndexTest(BaseMRRCTest):
    def setUp(self):
        super().setUp()
        # mock_s3 is used to generate expected content
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET)

    def tearDown(self):
        bucket = self.mock_s3.Bucket(TEST_BUCKET)
        try:
            bucket.objects.all().delete()
            bucket.delete()
        except ValueError:
            pass
        super().tearDown()

    def __prepare_s3(self):
        return boto3.resource('s3')

    def test_uploading_index(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(13, len(objs))

        actual_files = [obj.key for obj in objs]

        for f in CODE_FRAME_7_14_5_INDEXES:
            self.assertIn(f, actual_files)

        for obj in objs:
            self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
            self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(CODE_FRAME_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"-/\" title=\"-/\">-/</a>", index_content)
        self.assertIn("<a href=\"7.14.5/\" title=\"7.14.5/\">7.14.5/</a>", index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"@babel/\" title=\"@babel/\">@babel/</a>", index_content)
        self.assertNotIn("<a href=\"../\" title=\"../\">../</a>", index_content)

    def test_overlap_upload_index(self):
        self.__prepare_content()

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(17, len(objs))

        actual_files = [obj.key for obj in objs]

        for assert_file in CODE_FRAME_7_14_5_INDEXES:
            self.assertIn(assert_file, actual_files)

        for assert_file in CODE_FRAME_7_15_8_INDEXES:
            self.assertIn(assert_file, actual_files)

        indedx_obj = test_bucket.Object(CODE_FRAME_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"7.14.5/\" title=\"7.14.5/\">7.14.5/</a>", index_content)
        self.assertIn("<a href=\"7.15.8/\" title=\"7.15.8/\">7.15.8/</a>", index_content)
        self.assertIn("<a href=\"-/\" title=\"-/\">-/</a>", index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)

    def test_deletion_index(self):
        self.__prepare_content()

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(13, len(objs))

        actual_files = [obj.key for obj in objs]

        for assert_file in CODE_FRAME_7_15_8_INDEXES:
            self.assertIn(assert_file, actual_files)
        self.assertNotIn(CODE_FRAME_7_14_5_INDEX, actual_files)

        for obj in objs:
            self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
            self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(CODE_FRAME_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"7.15.8/\" title=\"7.15.8/\">7.15.8/</a>", index_content)
        self.assertIn("<a href=\"-/\" title=\"-/\">-/</a>", index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)
        self.assertNotIn("<a href=\"7.14.5/\" title=\"7.14.5/\">7.14.5/</a>", index_content)

        product_7_15_8 = "code-frame-7.15.8"
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        handle_npm_del(
            test_tgz, product_7_15_8, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def __prepare_content(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )
