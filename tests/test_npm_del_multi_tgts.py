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
from charon.constants import PROD_INFO_SUFFIX, DEFAULT_REGISTRY
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from charon.storage import CHECKSUM_META_KEY
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, PackageBaseTest
from tests.commons import TEST_BUCKET, CODE_FRAME_7_14_5_FILES, CODE_FRAME_META, TEST_BUCKET_2
from tests.constants import INPUTS


@mock_s3
class NPMDeleteMultiTgtsTest(PackageBaseTest):
    def setUp(self):
        super().setUp()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET_2)
        self.test_bucket_2 = self.mock_s3.Bucket(TEST_BUCKET_2)

    def tearDown(self):
        buckets = [TEST_BUCKET_2]
        self.cleanBuckets(buckets)
        super().tearDown()

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
        targets_ = [('', TEST_BUCKET, prefix, ''), ('', TEST_BUCKET_2, prefix, '')]
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5,
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )

        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]
            self.assertEqual(5, len(actual_files), msg=f'{bucket_name}')

            PREFIXED_7145_FILES = CODE_FRAME_7_14_5_FILES
            PREFIXED_FRAME_META = CODE_FRAME_META
            if prefix and prefix != "/":
                PREFIXED_7145_FILES = [
                    os.path.join(prefix, f) for f in CODE_FRAME_7_14_5_FILES
                ]
                PREFIXED_FRAME_META = os.path.join(prefix, CODE_FRAME_META)
            for f in PREFIXED_7145_FILES:
                self.assertNotIn(f, actual_files, msg=f'{bucket_name}')
            self.assertIn(PREFIXED_FRAME_META, actual_files, msg=f'{bucket_name}')

            for obj in objs:
                if not obj.key.endswith(PROD_INFO_SUFFIX):
                    self.assertIn(
                        CHECKSUM_META_KEY, obj.Object().metadata, msg=f'{bucket_name}'
                    )
                    self.assertNotEqual(
                        "", obj.Object().metadata[CHECKSUM_META_KEY].strip(), msg=f'{bucket_name}'
                    )

            product_7_15_8 = "code-frame-7.15.8"
            meta_obj = bucket.Object(PREFIXED_FRAME_META)
            # self.check_product(meta_obj.key, [product_7_15_8])
            meta_content_client = str(meta_obj.get()["Body"].read(), "utf-8")
            self.assertIn(
                "\"name\": \"@babel/code-frame\"", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertIn(
                "\"description\": \"Generate errors that contain a code frame that point to "
                "source locations.\"", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertIn(
                "\"repository\": {\"type\": \"git\", \"url\": "
                "\"https://github.com/babel/babel.git\"",
                meta_content_client, msg=f'{bucket_name}'
            )
            self.assertIn(
                "\"version\": \"7.15.8\"", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertNotIn(
                "\"version\": \"7.14.5\"", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertIn(
                "\"versions\": {\"7.15.8\":", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertNotIn(
                "\"7.14.5\": {\"name\":", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertIn(
                "\"license\": \"MIT\"", meta_content_client, msg=f'{bucket_name}'
            )
            self.assertIn(
                "\"dist_tags\": {\"latest\": \"7.15.8\"}",
                meta_content_client, msg=f'{bucket_name}'
            )

        test_tgz = os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        handle_npm_del(
            test_tgz, product_7_15_8,
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )
        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            self.assertEqual(0, len(objs))

    def __prepare_content(self, prefix: str = None):
        targets_ = [('', TEST_BUCKET, prefix, DEFAULT_REGISTRY),
                    ('', TEST_BUCKET_2, prefix, DEFAULT_REGISTRY)]
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )

        test_tgz = os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8,
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )
