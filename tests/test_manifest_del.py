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
import os

from moto import mock_s3

from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from tests.base import PackageBaseTest
from tests.commons import (
    TEST_BUCKET, TEST_MANIFEST_BUCKET, TEST_TARGET, COMMONS_CLIENT_456_MANIFEST,
    CODE_FRAME_7_14_5_MANIFEST
)


@mock_s3
class ManifestDeleteTest(PackageBaseTest):

    def test_maven_manifest_delete(self):
        self.__prepare_maven_content()

        uploaded_manifest = list(self.test_manifest_bucket.objects.all())
        manifests = [obj.key for obj in uploaded_manifest]
        self.assertEqual(1, len(manifests))
        self.assertIn(COMMONS_CLIENT_456_MANIFEST, manifests)

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product,
            targets=[(TEST_TARGET, TEST_BUCKET, None)],
            dir_=self.tempdir,
            do_index=False,
            manifest_bucket_name=TEST_MANIFEST_BUCKET
        )
        uploaded_manifest = list(self.test_manifest_bucket.objects.all())
        manifests = [obj.key for obj in uploaded_manifest]
        self.assertEqual(0, len(manifests))

    def test_npm_manifest_delete(self):
        self.__prepare_npm_content()

        uploaded_manifest = list(self.test_manifest_bucket.objects.all())
        manifests = [obj.key for obj in uploaded_manifest]
        self.assertEqual(1, len(manifests))
        self.assertIn(CODE_FRAME_7_14_5_MANIFEST, manifests)

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product,
            targets=[(TEST_TARGET, TEST_BUCKET, None)],
            dir_=self.tempdir,
            do_index=False,
            manifest_bucket_name=TEST_MANIFEST_BUCKET
        )
        uploaded_manifest = list(self.test_manifest_bucket.objects.all())
        manifests = [obj.key for obj in uploaded_manifest]
        self.assertEqual(0, len(manifests))

    def __prepare_maven_content(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            targets=[(TEST_TARGET, TEST_BUCKET, None)],
            dir_=self.tempdir,
            do_index=False,
            manifest_bucket_name=TEST_MANIFEST_BUCKET
        )

    def __prepare_npm_content(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product,
            targets=[(TEST_TARGET, TEST_BUCKET, None)],
            dir_=self.tempdir,
            do_index=False,
            manifest_bucket_name=TEST_MANIFEST_BUCKET
        )
