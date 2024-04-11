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
from charon.constants import DEFAULT_REGISTRY
from tests.base import PackageBaseTest
from tests.commons import TEST_BUCKET
from tests.constants import INPUTS
import logging

logger = logging.getLogger(f"charon.tests.{__name__}")

CODE_FRAME_FILES_REDHAT = [
    "@redhat/code-frame/7.14.5/package.json",
    "@redhat/code-frame/-/code-frame-7.14.5-multi-pkgs.tgz"
]

CODE_FRAME_META_REDHAT = "@redhat/code-frame/package.json"

CODE_FRAME_FILES_BABEL = [
    "@babel/code-frame/7.14.5/package.json",
    "@babel/code-frame/-/code-frame-7.14.5-no-root-pkg.tgz"
]

CODE_FRAME_META_BABEL = "@babel/code-frame/package.json"


@mock_aws
class NPMUploadTest(PackageBaseTest):

    def test_npm_uploads_multi_pkgjson_with_root(self):
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5-multi-pkgs.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=[('', TEST_BUCKET, '', DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        logger.debug("actual_files: %s", actual_files)
        self.assertEqual(5, len(actual_files))

        for f in CODE_FRAME_FILES_REDHAT:
            self.assertIn(f, actual_files)
            self.check_product(f, [product_7_14_5])
        self.assertIn(CODE_FRAME_META_REDHAT, actual_files)

        meta_obj_client = test_bucket.Object(CODE_FRAME_META_REDHAT)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@redhat/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to "
                      "source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": "
                      "\"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {", meta_content_client)
        self.assertIn("\"7.14.5\": {\"name\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertNotIn("\"dist_tags\":", meta_content_client)

    def test_npm_uploads_multi_pkgjson_with_no_root(self):
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5-no-root-pkg.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=[('', TEST_BUCKET, '', DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        logger.debug("actual_files: %s", actual_files)
        self.assertEqual(5, len(actual_files))

        for f in CODE_FRAME_FILES_BABEL:
            self.assertIn(f, actual_files)
            self.check_product(f, [product_7_14_5])
        self.assertIn(CODE_FRAME_META_BABEL, actual_files)

        meta_obj_client = test_bucket.Object(CODE_FRAME_META_BABEL)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@babel/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to "
                      "source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": "
                      "\"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {", meta_content_client)
        self.assertIn("\"7.14.5\": {\"name\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertNotIn("\"dist_tags\":", meta_content_client)
