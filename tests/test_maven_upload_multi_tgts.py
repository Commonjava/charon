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
from typing import List, Tuple
from charon.pkgs.maven import handle_maven_uploading
from charon.utils.strings import remove_prefix
from tests.base import SHORT_TEST_PREFIX, LONG_TEST_PREFIX, PackageBaseTest
from tests.commons import (
    TEST_BUCKET, COMMONS_CLIENT_456_FILES, COMMONS_CLIENT_459_FILES,
    COMMONS_CLIENT_METAS, COMMONS_LOGGING_FILES, COMMONS_LOGGING_METAS,
    NON_MVN_FILES, ARCHETYPE_CATALOG, ARCHETYPE_CATALOG_FILES,
    COMMONS_CLIENT_456_MVN_NUM, COMMONS_CLIENT_MVN_NUM,
    COMMONS_CLIENT_META_NUM, TEST_BUCKET_2
)
from moto import mock_aws
import os

from tests.constants import INPUTS


@mock_aws
class MavenUploadMultiTgtsTest(PackageBaseTest):
    def setUp(self):
        super().setUp()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET_2)
        self.test_bucket_2 = self.mock_s3.Bucket(TEST_BUCKET_2)

    def tearDown(self):
        buckets = [TEST_BUCKET_2]
        self.cleanBuckets(buckets)
        super().tearDown()

    def test_fresh_upload(self):
        self.__test_prefix_upload(
            [('', TEST_BUCKET, ""), ('', TEST_BUCKET_2, "", '')]
        )

    def test_short_prefix_upload(self):
        self.__test_prefix_upload(
            [('', TEST_BUCKET, SHORT_TEST_PREFIX), ('', TEST_BUCKET_2, SHORT_TEST_PREFIX, '')]
        )

    def test_long_prefix_upload(self):
        self.__test_prefix_upload(
            [('', TEST_BUCKET, LONG_TEST_PREFIX), ('', TEST_BUCKET_2, LONG_TEST_PREFIX, '')]
        )

    def test_root_prefix_upload(self):
        self.__test_prefix_upload([('', TEST_BUCKET, "/", ''),
                                   ('', TEST_BUCKET_2, "/", '')])

    def test_overlap_upload(self):
        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        targets_ = [
            ('', TEST_BUCKET, '', ''), ('', TEST_BUCKET_2, '', '')
        ]
        handle_maven_uploading(
            test_zip, product_456,
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )

        test_zip = os.path.join(INPUTS, "commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )

        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]
            # need to double mvn num because of .prodinfo files
            expected = COMMONS_CLIENT_MVN_NUM * 2 + COMMONS_CLIENT_META_NUM
            self.assertEqual(
                expected,
                len(actual_files),
                msg=f'{bucket_name}'
            )

            filesets = [
                COMMONS_CLIENT_METAS, COMMONS_CLIENT_456_FILES,
                COMMONS_CLIENT_459_FILES,
                ARCHETYPE_CATALOG_FILES
            ]
            for fileset in filesets:
                for f in fileset:
                    self.assertIn(f, actual_files, msg=f'{bucket_name}')

            product_mix = [product_456, product_459]
            for f in COMMONS_LOGGING_FILES:
                self.assertIn(f, actual_files, msg=f'{bucket_name}')
                self.check_product(f, product_mix, msg=f'{bucket_name}')
            for f in COMMONS_LOGGING_METAS:
                self.assertIn(f, actual_files, msg=f'{bucket_name}')

            meta_obj_client = self.test_bucket.Object(COMMONS_CLIENT_METAS[0])
            meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<groupId>org.apache.httpcomponents</groupId>", meta_content_client,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<artifactId>httpclient</artifactId>", meta_content_client,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<latest>4.5.9</latest>", meta_content_client,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<release>4.5.9</release>", meta_content_client,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<version>4.5.6</version>", meta_content_client,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<version>4.5.9</version>", meta_content_client,
                msg=f'{bucket_name}'
            )

            meta_obj_logging = self.test_bucket.Object(COMMONS_LOGGING_METAS[0])
            meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<groupId>commons-logging</groupId>", meta_content_logging,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<artifactId>commons-logging</artifactId>", meta_content_logging,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<version>1.2</version>", meta_content_logging,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<latest>1.2</latest>", meta_content_logging,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<release>1.2</release>", meta_content_logging,
                msg=f'{bucket_name}'
            )

            catalog = self.test_bucket.Object(ARCHETYPE_CATALOG)
            cat_content = str(catalog.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<version>4.5.6</version>", cat_content,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<version>4.5.9</version>", cat_content,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<artifactId>httpclient</artifactId>", cat_content,
                msg=f'{bucket_name}'
            )
            self.assertIn(
                "<groupId>org.apache.httpcomponents</groupId>", cat_content,
                msg=f'{bucket_name}'
            )

    def test_ignore_upload(self):
        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        targets_ = [
            ('', TEST_BUCKET, '', ''), ('', TEST_BUCKET_2, '', '')
        ]
        handle_maven_uploading(
            test_zip, product_456, [".*.sha1"],
            buckets=targets_,
            dir_=self.tempdir, do_index=False
        )

        ignored_files = [
                "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
                "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1",
                "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
                "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
                "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1"
            ]
        not_ignored = [e for e in COMMONS_CLIENT_456_FILES if e not in ignored_files]
        not_ignored.extend(
                [e for e in COMMONS_LOGGING_FILES if e not in ignored_files])
        for target in targets_:
            bucket_name = target[1]
            bucket = self.mock_s3.Bucket(bucket_name)
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]

            # need to double mvn num because of .prodinfo files
            self.assertEqual(
                len(not_ignored) * 2 + COMMONS_CLIENT_META_NUM, len(actual_files),
                msg=f'{bucket_name}'
            )
            for f in not_ignored:
                self.assertIn(f, actual_files, msg=f'{bucket_name}')
            for f in ignored_files:
                self.assertNotIn(f, actual_files, msg=f'{bucket_name}')

    def __test_prefix_upload(self, targets: List[Tuple[str, str, str, str]]):
        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            buckets=targets,
            dir_=self.tempdir,
            do_index=False
        )

        for target in targets:
            bucket = self.mock_s3.Bucket(target[1])
            objs = list(bucket.objects.all())
            actual_files = [obj.key for obj in objs]
            # need to double mvn num because of .prodinfo files
            expected = COMMONS_CLIENT_456_MVN_NUM * 2 + COMMONS_CLIENT_META_NUM
            self.assertEqual(
                expected, len(actual_files),
                msg=f"{bucket.name}"
            )

            prefix_ = remove_prefix(target[2], "/")
            PREFIXED_COMMONS_CLIENT_456_FILES = [
                os.path.join(prefix_, f) for f in COMMONS_CLIENT_456_FILES]
            PREFIXED_COMMONS_CLIENT_METAS = [
                os.path.join(prefix_, f) for f in COMMONS_CLIENT_METAS]
            PREFIXED_COMMONS_LOGGING_FILES = [
                os.path.join(prefix_, f) for f in COMMONS_LOGGING_FILES]
            PREFIXED_COMMONS_LOGGING_METAS = [
                os.path.join(prefix_, f) for f in COMMONS_LOGGING_METAS]
            PREFIXED_ARCHETYPE_CATALOG_FILES = [
                os.path.join(prefix_, f) for f in ARCHETYPE_CATALOG_FILES]
            file_set = [
                *PREFIXED_COMMONS_CLIENT_456_FILES, *PREFIXED_COMMONS_CLIENT_METAS,
                *PREFIXED_COMMONS_LOGGING_FILES, *PREFIXED_COMMONS_LOGGING_METAS,
                *PREFIXED_ARCHETYPE_CATALOG_FILES
            ]
            for f in file_set:
                self.assertIn(f, actual_files, msg=f"{bucket.name}")

            PREFIXED_NON_MVN_FILES = [
                os.path.join(prefix_, f) for f in NON_MVN_FILES]
            for f in PREFIXED_NON_MVN_FILES:
                self.assertNotIn(f, actual_files, msg=f"{bucket.name}")

            self.check_content(objs, [product], msg=f"{bucket.name}")

            meta_obj_client = self.test_bucket.Object(PREFIXED_COMMONS_CLIENT_METAS[0])
            meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<groupId>org.apache.httpcomponents</groupId>", meta_content_client,
                msg=f"{bucket.name}"
            )
            self.assertIn("<artifactId>httpclient</artifactId>", meta_content_client,
                          msg=f"{bucket.name}")
            self.assertIn("<version>4.5.6</version>", meta_content_client,
                          msg=f"{bucket.name}")
            self.assertIn("<latest>4.5.6</latest>", meta_content_client,
                          msg=f"{bucket.name}")
            self.assertIn("<release>4.5.6</release>", meta_content_client,
                          msg=f"{bucket.name}")
            self.assertNotIn("<version>4.5.9</version>", meta_content_client,
                             msg=f"{bucket.name}")

            meta_obj_logging = self.test_bucket.Object(PREFIXED_COMMONS_LOGGING_METAS[0])
            meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<groupId>commons-logging</groupId>", meta_content_logging,
                msg=f"{bucket.name}"
            )
            self.assertIn(
                "<artifactId>commons-logging</artifactId>", meta_content_logging,
                msg=f"{bucket.name}"
            )
            self.assertIn(
                "<version>1.2</version>", meta_content_logging,
                msg=f"{bucket.name}"
            )
            self.assertIn(
                "<latest>1.2</latest>", meta_content_logging,
                msg=f"{bucket.name}"
            )
            self.assertIn(
                "<release>1.2</release>", meta_content_logging,
                msg=f"{bucket.name}"
            )

            catalog = self.test_bucket.Object(PREFIXED_ARCHETYPE_CATALOG_FILES[0])
            cat_content = str(catalog.get()["Body"].read(), "utf-8")
            self.assertIn(
                "<version>4.5.6</version>", cat_content,
                msg=f"{bucket.name}"
            )
            self.assertIn(
                "<artifactId>httpclient</artifactId>", cat_content,
                msg=f"{bucket.name}"
            )
            self.assertIn(
                "<groupId>org.apache.httpcomponents</groupId>", cat_content,
                msg=f"{bucket.name}"
            )
