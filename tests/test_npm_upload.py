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

from moto import mock_aws

from charon.pkgs.npm import handle_npm_uploading
from charon.pkgs.pkg_utils import is_metadata
from charon.storage import CHECKSUM_META_KEY
from charon.constants import PROD_INFO_SUFFIX, DEFAULT_REGISTRY
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, PackageBaseTest
from tests.commons import (
    TEST_BUCKET, CODE_FRAME_7_14_5_FILES,
    CODE_FRAME_7_15_8_FILES, CODE_FRAME_META
)
from tests.constants import INPUTS


@mock_aws
class NPMUploadTest(PackageBaseTest):

    def test_npm_upload(self):
        self.__test_prefix()

    def test_upload_with_short_prefix(self):
        self.__test_prefix(SHORT_TEST_PREFIX)

    def test_upload_with_long_prefix(self):
        self.__test_prefix(LONG_TEST_PREFIX)

    def test_upload_with_root_prefix(self):
        self.__test_prefix("/")

    def test_double_uploads(self):
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, '', DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )
        test_tgz = os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8,
            targets=[('', TEST_BUCKET, '', DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(9, len(actual_files))

        for f in CODE_FRAME_7_14_5_FILES:
            self.assertIn(f, actual_files)
            self.check_product(f, [product_7_14_5])
        for f in CODE_FRAME_7_15_8_FILES:
            self.assertIn(f, actual_files)
            self.check_product(f, [product_7_15_8])
        self.assertIn(CODE_FRAME_META, actual_files)
        # self.check_product(CODE_FRAME_META, product_mix)

        meta_obj_client = test_bucket.Object(CODE_FRAME_META)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@babel/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to "
                      "source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": "
                      "\"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.15.8\"", meta_content_client)
        self.assertIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {", meta_content_client)
        self.assertIn("\"7.15.8\": {\"name\":", meta_content_client)
        self.assertIn("\"7.14.5\": {\"name\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertIn("\"dist-tags\": {\"latest\": \"7.15.8\"}", meta_content_client)
        self.assertNotIn("\"dist_tags\":", meta_content_client)

    def __test_prefix(self, prefix: str = None):
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(5, len(actual_files))

        PREFIXED_7145_FILES = CODE_FRAME_7_14_5_FILES
        PREFIXED_FRAME_META = CODE_FRAME_META
        if prefix and prefix != "/":
            PREFIXED_7145_FILES = [
                os.path.join(prefix, f) for f in CODE_FRAME_7_14_5_FILES
            ]
            PREFIXED_FRAME_META = os.path.join(prefix, CODE_FRAME_META)
        for f in PREFIXED_7145_FILES:
            self.assertIn(f, actual_files)
        self.assertIn(PREFIXED_FRAME_META, actual_files)

        for o in objs:
            if not o.key.endswith(PROD_INFO_SUFFIX):
                obj = o.Object()
                if not is_metadata(o.key):
                    self.check_product(o.key, [product_7_14_5])
                self.assertIn(CHECKSUM_META_KEY, obj.metadata)
                self.assertNotEqual("", obj.metadata[CHECKSUM_META_KEY].strip())

        meta_obj_client = test_bucket.Object(PREFIXED_FRAME_META)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@babel/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to "
                      "source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": "
                      "\"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {\"7.14.5\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertIn("\"dist-tags\": {\"latest\": \"7.14.5\"}", meta_content_client)
        self.assertNotIn("\"dist_tags\":", meta_content_client)
