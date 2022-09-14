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
from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from charon.constants import DEFAULT_REGISTRY
from tests.base import PackageBaseTest
from tests.commons import TEST_BUCKET
from moto import mock_s3
import os


@mock_s3
class PkgsDryRunTest(PackageBaseTest):
    def test_maven_upload_dry_run(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            buckets=[(None, TEST_BUCKET, None, None)],
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def test_maven_delete_dry_run(self):
        self.__prepare_maven_content()

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            buckets=[(None, TEST_BUCKET, None, None)],
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(50, len(objs))

    def test_npm_upload_dry_run(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=[(None, TEST_BUCKET, None, DEFAULT_REGISTRY)],
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def test_npm_deletion_dry_run(self):
        self.__prepare_npm_content()

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5,
            buckets=[(None, TEST_BUCKET, None, None)],
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(11, len(objs))

    def __prepare_maven_content(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            buckets=[(None, TEST_BUCKET, None, None)],
            dir_=self.tempdir
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            buckets=[(None, TEST_BUCKET, None, None)],
            dir_=self.tempdir
        )

    def __prepare_npm_content(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=[(None, TEST_BUCKET, None, DEFAULT_REGISTRY)],
            dir_=self.tempdir
        )

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8,
            buckets=[(None, TEST_BUCKET, None, DEFAULT_REGISTRY)],
            dir_=self.tempdir
        )
