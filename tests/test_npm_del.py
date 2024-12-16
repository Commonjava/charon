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
from charon.constants import PROD_INFO_SUFFIX, DEFAULT_REGISTRY
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from charon.storage import CHECKSUM_META_KEY
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, PackageBaseTest
from tests.commons import TEST_BUCKET, CODE_FRAME_7_14_5_FILES, CODE_FRAME_META
from tests.constants import INPUTS


@mock_aws
class NPMDeleteTest(PackageBaseTest):
    def test_npm_deletion(self):
        self.__test_prefix()

    def test_npm_deletion_with_short_prefix(self):
        self.__test_prefix(SHORT_TEST_PREFIX)

    def test_npm_deletion_with_long_prefix(self):
        self.__test_prefix(LONG_TEST_PREFIX)

    def test_npm_deletion_with_root_prefix(self):
        self.__test_prefix("/")

    def __test_prefix(self, prefix: str = None):
        self.__prepare_content(prefix)

        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, prefix, '')],
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
            self.assertNotIn(f, actual_files)
        self.assertIn(PREFIXED_FRAME_META, actual_files)

        for obj in objs:
            if not obj.key.endswith(PROD_INFO_SUFFIX):
                self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
                self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        product_7_15_8 = "code-frame-7.15.8"
        meta_obj = test_bucket.Object(PREFIXED_FRAME_META)
        # self.check_product(meta_obj.key, [product_7_15_8])
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@babel/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to "
                      "source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": "
                      "\"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.15.8\"", meta_content_client)
        self.assertNotIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {\"7.15.8\":", meta_content_client)
        self.assertNotIn("\"7.14.5\": {\"name\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertIn("\"dist-tags\": {\"latest\": \"7.15.8\"}", meta_content_client)

        test_tgz = os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        handle_npm_del(
            test_tgz, product_7_15_8,
            targets=[('', TEST_BUCKET, prefix, '')],
            dir_=self.tempdir, do_index=False
        )
        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def __prepare_content(self, prefix: str = None):
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )

        test_tgz = os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8,
            targets=[('', TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
            dir_=self.tempdir, do_index=False
        )

    def test_overlap_prefix_del(self):
        self.__prepare_content_backstage()

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(18, len(actual_files))

        meta_obj = test_bucket.Object("@janus-idp/backstage-plugin-orchestrator/package.json")
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@janus-idp/backstage-plugin-orchestrator\"", meta_content_client)
        self.assertIn("\"version\": \"1.21.102\"", meta_content_client)
        self.assertIn("\"version\": \"1.21.103\"", meta_content_client)
        self.assertIn("\"1.21.103\": {\"name\":", meta_content_client)

        meta_obj = test_bucket.Object(
            "@janus-idp/backstage-plugin-orchestrator-backend-dynamic/package.json")
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn(
            "\"name\": \"@janus-idp/backstage-plugin-orchestrator-backend-dynamic\"",
            meta_content_client)
        self.assertIn("\"version\": \"0.0.1\"", meta_content_client)
        self.assertIn("\"version\": \"2.3.0\"", meta_content_client)
        self.assertIn("\"2.3.0\": {\"name\":", meta_content_client)

        test_prod = "backstage-plugin-orchestrator-1.21.103"
        test_tgz = os.path.join(INPUTS, test_prod+".tgz")
        handle_npm_del(
            test_tgz, test_prod,
            targets=[('', TEST_BUCKET, None, '')],
            dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(14, len(actual_files))

        meta_obj = test_bucket.Object("@janus-idp/backstage-plugin-orchestrator/package.json")
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@janus-idp/backstage-plugin-orchestrator\"", meta_content_client)
        self.assertIn("\"version\": \"1.21.102\"", meta_content_client)
        self.assertNotIn("\"version\": \"1.21.103\"", meta_content_client)
        self.assertNotIn("\"1.21.103\": {\"name\":", meta_content_client)

        meta_obj = test_bucket.Object(
            "@janus-idp/backstage-plugin-orchestrator-backend-dynamic/package.json")
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn(
            "\"name\": \"@janus-idp/backstage-plugin-orchestrator-backend-dynamic\"",
            meta_content_client)
        self.assertIn("\"version\": \"0.0.1\"", meta_content_client)
        self.assertIn("\"version\": \"2.3.0\"", meta_content_client)
        self.assertIn("\"2.3.0\": {\"name\":", meta_content_client)

        test_prod = "backstage-plugin-orchestrator-backend-dynamic-2.3.0"
        test_tgz = os.path.join(INPUTS, test_prod+".tgz")
        handle_npm_del(
            test_tgz, test_prod,
            targets=[('', TEST_BUCKET, None, '')],
            dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(10, len(actual_files))

        meta_obj = test_bucket.Object(
            "@janus-idp/backstage-plugin-orchestrator/package.json")
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn(
            "\"name\": \"@janus-idp/backstage-plugin-orchestrator\"",
            meta_content_client)
        self.assertIn("\"version\": \"1.21.102\"", meta_content_client)
        self.assertNotIn("\"version\": \"1.21.103\"", meta_content_client)
        self.assertNotIn("\"1.21.103\": {\"name\":", meta_content_client)

        meta_obj = test_bucket.Object(
            "@janus-idp/backstage-plugin-orchestrator-backend-dynamic/package.json")
        meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
        self.assertIn(
            "\"name\": \"@janus-idp/backstage-plugin-orchestrator-backend-dynamic\"",
            meta_content_client)
        self.assertIn("\"version\": \"0.0.1\"", meta_content_client)
        self.assertNotIn("\"version\": \"2.3.0\"", meta_content_client)
        self.assertNotIn("\"2.3.0\": {\"name\":", meta_content_client)

    def __prepare_content_backstage(self, prefix: str = None):
        test_prods = [
            "backstage-plugin-orchestrator-1.21.102",
            "backstage-plugin-orchestrator-1.21.103",
            "backstage-plugin-orchestrator-backend-dynamic-0.0.1",
            "backstage-plugin-orchestrator-backend-dynamic-2.3.0"
        ]
        for p in test_prods:
            test_tgz = os.path.join(INPUTS, p+".tgz")
            handle_npm_uploading(
                test_tgz, p,
                targets=[('', TEST_BUCKET, prefix, DEFAULT_REGISTRY)],
                dir_=self.tempdir, do_index=False
            )
