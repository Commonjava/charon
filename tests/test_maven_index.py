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
from charon.constants import PROD_INFO_SUFFIX
from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.storage import CHECKSUM_META_KEY
from charon.utils.strings import remove_prefix
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, PackageBaseTest
from tests.commons import (
    TEST_BUCKET, COMMONS_CLIENT_456_INDEXES, COMMONS_CLIENT_459_INDEXES,
    COMMONS_LOGGING_INDEXES, COMMONS_CLIENT_INDEX, COMMONS_CLIENT_456_INDEX,
    COMMONS_LOGGING_INDEX, COMMONS_ROOT_INDEX
)
from moto import mock_s3
import os


@mock_s3
class MavenFileIndexTest(PackageBaseTest):

    def test_uploading_index(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]

        self.assertEqual(41, len(actual_files))

        for f in COMMONS_LOGGING_INDEXES:
            self.assertIn(f, actual_files)

        for f in COMMONS_CLIENT_456_INDEXES:
            self.assertIn(f, actual_files)

        self.check_content(objs, [product])

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.6/\" title=\"4.5.6/\">4.5.6/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content
        )
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../\" title=\"../\">../</a>", index_content)

    def test_overlap_upload_index(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(50, len(objs))

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.6/\" title=\"4.5.6/\">4.5.6/</a>", index_content)
        self.assertIn("<a href=\"4.5.9/\" title=\"4.5.9/\">4.5.9/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_LOGGING_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"1.2/\" title=\"1.2/\">1.2/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../\" title=\"../\">../</a>", index_content)

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
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir,
            prefix=prefix
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(41, len(actual_files))

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

        self.check_content(objs, [product])

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_CLIENT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.6/\" title=\"4.5.6/\">4.5.6/</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content
        )
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_ROOT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../\" title=\"../\">../</a>", index_content)

    def test_deletion_index(self):
        self.__prepare_content()

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(41, len(actual_files))

        for assert_file in COMMONS_CLIENT_459_INDEXES:
            self.assertIn(assert_file, actual_files)

        for assert_file in COMMONS_LOGGING_INDEXES:
            self.assertIn(assert_file, actual_files)

        self.assertNotIn(COMMONS_CLIENT_456_INDEX, actual_files)

        for obj in objs:
            if not obj.key.endswith(PROD_INFO_SUFFIX):
                file_obj = obj.Object()
                self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
                self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.9/\" title=\"4.5.9/\">4.5.9/</a>", index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertNotIn("<a href=\"4.5.6/\" title=\"4.5.6/\">4.5.6/</a>", index_content)

        indedx_obj = test_bucket.Object(COMMONS_ROOT_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        product_459 = "commons-client-4.5.9"
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        handle_maven_del(
            test_zip, product_459, bucket_name=TEST_BUCKET, dir_=self.tempdir
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
            bucket_name=TEST_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )

        product_459 = "commons-client-4.5.9"
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(41, len(actual_files))

        prefix_ = remove_prefix(prefix, "/")
        PREFIXED_459_INDEXES = [os.path.join(prefix_, i) for i in COMMONS_CLIENT_459_INDEXES]
        for assert_file in PREFIXED_459_INDEXES:
            self.assertIn(assert_file, actual_files)

        PREFIXED_LOGGING_INDEXES = [os.path.join(prefix_, i) for i in COMMONS_LOGGING_INDEXES]
        for assert_file in PREFIXED_LOGGING_INDEXES:
            self.assertIn(assert_file, actual_files)

        self.assertNotIn(os.path.join(prefix_, COMMONS_CLIENT_456_INDEX), actual_files)

        self.check_content(objs, [product_459])

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_CLIENT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"4.5.9/\" title=\"4.5.9/\">4.5.9/</a>", index_content)
        self.assertIn("<a href=\"../\" title=\"../\">../</a>", index_content)
        self.assertIn(
            "<a href=\"maven-metadata.xml\" title=\"maven-metadata.xml\">maven-metadata.xml</a>",
            index_content)
        self.assertNotIn("<a href=\"4.5.6/\" title=\"4.5.6/\">4.5.6/</a>", index_content)

        indedx_obj = test_bucket.Object(os.path.join(prefix_, COMMONS_ROOT_INDEX))
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn("<a href=\"org/\" title=\"org/\">org/</a>", index_content)
        self.assertIn(
            "<a href=\"commons-logging/\" "
            "title=\"commons-logging/\">commons-logging/</a>",
            index_content
        )
        self.assertNotIn("<a href=\"../\" title=\"../\">../</a>", index_content)

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        handle_maven_del(
            test_zip, product_459,
            bucket_name=TEST_BUCKET,
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
            bucket_name=TEST_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_BUCKET,
            prefix=prefix,
            dir_=self.tempdir
        )
