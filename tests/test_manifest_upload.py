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

from charon.pkgs.maven import handle_maven_uploading
from charon.pkgs.npm import handle_npm_uploading
from charon.constants import DEFAULT_REGISTRY
from tests.base import PackageBaseTest
from tests.commons import (
    TEST_BUCKET, TEST_MANIFEST_BUCKET, TEST_TARGET, COMMONS_CLIENT_456_MVN_NUM,
    COMMONS_CLIENT_META_NUM, COMMONS_CLIENT_456_MANIFEST, COMMONS_CLIENT_456_FILES,
    COMMONS_LOGGING_FILES, CODE_FRAME_7_14_5_MANIFEST, CODE_FRAME_7_14_5_FILES
)


@mock_s3
class ManifestUploadTest(PackageBaseTest):

    def test_maven_manifest_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            buckets=[(TEST_TARGET, TEST_BUCKET, None, None)],
            dir_=self.tempdir,
            do_index=False,
            manifest_bucket_name=TEST_MANIFEST_BUCKET
        )

        uploaded_contents = list(self.test_bucket.objects.all())
        actual_files = [obj.key for obj in uploaded_contents]
        self.assertEqual(
            COMMONS_CLIENT_456_MVN_NUM * 2 + COMMONS_CLIENT_META_NUM,
            len(actual_files)
        )

        uploaded_manifest = list(self.test_manifest_bucket.objects.all())
        manifests = [obj.key for obj in uploaded_manifest]
        self.assertEqual(1, len(manifests))
        self.assertIn(COMMONS_CLIENT_456_MANIFEST, manifests)

        manifest_obj = self.test_manifest_bucket.Object(COMMONS_CLIENT_456_MANIFEST)
        manifest_content = str(manifest_obj.get()["Body"].read(), "utf-8")
        for f in COMMONS_CLIENT_456_FILES:
            self.assertIn(f, manifest_content)
        for f in COMMONS_LOGGING_FILES:
            self.assertIn(f, manifest_content)

    def test_npm_manifest_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product = "code-frame-7.14.5"
        handle_npm_uploading(
            test_zip, product,
            buckets=[(TEST_TARGET, TEST_BUCKET, None, DEFAULT_REGISTRY)],
            dir_=self.tempdir,
            do_index=False,
            manifest_bucket_name=TEST_MANIFEST_BUCKET
        )

        uploaded_contents = list(self.test_bucket.objects.all())
        actual_files = [obj.key for obj in uploaded_contents]
        self.assertEqual(
            len(CODE_FRAME_7_14_5_FILES) * 2 + 1,
            len(actual_files)
        )

        uploaded_manifest = list(self.test_manifest_bucket.objects.all())
        manifests = [obj.key for obj in uploaded_manifest]
        self.assertEqual(1, len(manifests))
        self.assertIn(CODE_FRAME_7_14_5_MANIFEST, manifests)

        manifest_obj = self.test_manifest_bucket.Object(CODE_FRAME_7_14_5_MANIFEST)
        manifest_content = str(manifest_obj.get()["Body"].read(), "utf-8")
        for f in CODE_FRAME_7_14_5_FILES:
            self.assertIn(f, manifest_content)
