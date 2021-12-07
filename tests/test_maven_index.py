"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.pkgs.pkg_utils import is_metadata
from charon.storage import CHECKSUM_META_KEY, PRODUCT_META_KEY
from charon.utils.strings import remove_prefix
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, BaseTest
from tests.commons import (
    TEST_MVN_BUCKET, COMMONS_CLIENT_456_INDEXES, COMMONS_CLIENT_459_INDEXES,
    COMMONS_LOGGING_INDEXES, COMMONS_CLIENT_INDEX, COMMONS_CLIENT_456_INDEX,
    COMMONS_LOGGING_INDEX, COMMONS_ROOT_INDEX
)
from moto import mock_s3
import boto3
import os


@mock_s3
class MavenFileIndexTest(BaseTest):
    def setUp(self):
        super().setUp()
        # mock_s3 is used to generate expected content
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=TEST_MVN_BUCKET)

    def tearDown(self):
        bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        try:
            bucket.objects.all().delete()
            bucket.delete()
        except ValueError:
            pass
        super().tearDown()

    def __prepare_s3(self):
        return boto3.resource('s3')

    def test_uploading_index(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_MVN_BUCKET,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(27, len(actual_files))

        for f in COMMONS_LOGGING_INDEXES:
            self.assertIn(f, actual_files)

        for f in COMMONS_CLIENT_456_INDEXES:
            self.assertIn(f, actual_files)

        for obj in objs:
            file_obj = obj.Object()
            if not is_metadata(file_obj.key):
                self.assertEqual(product, file_obj.metadata[PRODUCT_META_KEY])
            else:
                self.assertNotIn(PRODUCT_META_KEY, file_obj.metadata)
            self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
            self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.6/index.html\" title=\"4.5.6/\">4.5.6/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content
        )
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/index.html\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/index.html\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

    def test_overlap_upload_index(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456, bucket_name=TEST_MVN_BUCKET, dir_=self.tempdir
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_MVN_BUCKET,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(32, len(objs))

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.6/index.html\" title=\"4.5.6/\">4.5.6/</a>", index_content)
        self.assertIn("<a href=\"4.5.9/index.html\" title=\"4.5.9/\">4.5.9/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_LOGGING_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"1.2/index.html\" title=\"1.2/\">1.2/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/index.html\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/index.html\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

    def test_upload_index_with_short_prefix(self):
        self.__test_upload_index_with_prefix(SHORT_TEST_PREFIX)

    def test_upload_index_with_long_prefix(self):
        self.__test_upload_index_with_prefix(LONG_TEST_PREFIX)

    def test_upload_index_with_root_prefix(self):
        self.__test_upload_index_with_prefix("/")

    def __test_upload_index_with_prefix(self, prefix: str):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_MVN_BUCKET,
            dir_=self.tempdir,
            prefix=prefix
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(27, len(actual_files))

        prefix_ = remove_prefix(prefix, "/")
        PREFIXED_LOGGING_INDEXES = [
            os.path.join(prefix_, i) for i in COMMONS_LOGGING_INDEXES
        ]
        for f in PREFIXED_LOGGING_INDEXES:
            self.assertIn(f, actual_files)

        PREFIXED_456_INDEXES = [
            os.path.join(prefix_, i) for i in COMMONS_CLIENT_456_INDEXES
        ]
        for f in PREFIXED_456_INDEXES:
            self.assertIn(f, actual_files)

        for obj in objs:
            file_obj = obj.Object()
            if not is_metadata(file_obj.key):
                self.assertEqual(product, file_obj.metadata[PRODUCT_META_KEY])
            else:
                self.assertNotIn(PRODUCT_META_KEY, file_obj.metadata)
            self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
            self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_CLIENT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.6/index.html\" title=\"4.5.6/\">4.5.6/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content
        )
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_ROOT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/index.html\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/index.html\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

    def test_deletion_index(self):
        self.__prepare_content()

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            bucket_name=TEST_MVN_BUCKET,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(27, len(actual_files))

        for assert_file in COMMONS_CLIENT_459_INDEXES:
            self.assertIn(assert_file, actual_files)

        for assert_file in COMMONS_LOGGING_INDEXES:
            self.assertIn(assert_file, actual_files)

        self.assertNotIn(COMMONS_CLIENT_456_INDEX, actual_files)

        for obj in objs:
            file_obj = obj.Object()
            self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
            self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.9/index.html\" title=\"4.5.9/\">4.5.9/</a>", index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertNotIn("<a href=\"4.5.6/index.html\" title=\"4.5.6/\">4.5.6/</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/index.html\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/index.html\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

        product_459 = "commons-client-4.5.9"
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        handle_maven_del(
            test_zip, product_459, bucket_name=TEST_MVN_BUCKET, dir_=self.tempdir
        )

        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def test_deletion_index_with_short_prefix(self):
        self.__test_deletion_index_with_prefix(SHORT_TEST_PREFIX)

    def test_deletion_index_with_long_prefix(self):
        self.__test_deletion_index_with_prefix(LONG_TEST_PREFIX)

    def test_deletion_index_with_root_prefix(self):
        self.__test_deletion_index_with_prefix("/")

    def __test_deletion_index_with_prefix(self, prefix: str):
        self.__prepare_content(prefix)

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            bucket_name=TEST_MVN_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(27, len(actual_files))

        prefix_ = remove_prefix(prefix, "/")
        PREFIXED_459_INDEXES = [os.path.join(prefix_, i) for i in COMMONS_CLIENT_459_INDEXES]
        for assert_file in PREFIXED_459_INDEXES:
            self.assertIn(assert_file, actual_files)

        PREFIXED_LOGGING_INDEXES = [os.path.join(prefix_, i) for i in COMMONS_LOGGING_INDEXES]
        for assert_file in PREFIXED_LOGGING_INDEXES:
            self.assertIn(assert_file, actual_files)

        self.assertNotIn(os.path.join(prefix_, COMMONS_CLIENT_456_INDEX), actual_files)

        for obj in objs:
            file_obj = obj.Object()
            if not is_metadata(file_obj.key):
                self.assertIn(PRODUCT_META_KEY, file_obj.metadata)
            else:
                self.assertNotIn(PRODUCT_META_KEY, file_obj.metadata)
            self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
            self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_CLIENT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.9/index.html\" title=\"4.5.9/\">4.5.9/</a>", index_content)
        self.assertIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertNotIn("<a href=\"4.5.6/index.html\" title=\"4.5.6/\">4.5.6/</a>", index_content)

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_ROOT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/index.html\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/index.html\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../index.html\" title=\"../\">../</a>", index_content)

        product_459 = "commons-client-4.5.9"
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        handle_maven_del(
            test_zip, product_459,
            bucket_name=TEST_MVN_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )

        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def __prepare_content(self, prefix=None):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            bucket_name=TEST_MVN_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_MVN_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )
