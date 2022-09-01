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
from charon.storage import PRODUCT_META_KEY, CHECKSUM_META_KEY
from charon.utils.strings import remove_prefix
from charon.constants import PROD_INFO_SUFFIX
from tests.base import LONG_TEST_PREFIX, SHORT_TEST_PREFIX, PackageBaseTest
from tests.commons import (
    TEST_BUCKET, COMMONS_CLIENT_456_FILES, COMMONS_CLIENT_459_FILES,
    COMMONS_CLIENT_METAS, COMMONS_LOGGING_FILES, COMMONS_LOGGING_METAS,
    ARCHETYPE_CATALOG, ARCHETYPE_CATALOG_FILES, COMMONS_CLIENT_459_MVN_NUM,
    COMMONS_CLIENT_META_NUM
)
from moto import mock_s3
import os


@mock_s3
class MavenDeleteTest(PackageBaseTest):
    def test_maven_deletion(self):
        self.__test_prefix_deletion("")

    def test_short_prefix_deletion(self):
        self.__test_prefix_deletion(SHORT_TEST_PREFIX)

    def test_long_prefix_deletion(self):
        self.__test_prefix_deletion(LONG_TEST_PREFIX)

    def test_root_prefix_deletion(self):
        self.__test_prefix_deletion("/")

    def test_ignore_del(self):
        self.__prepare_content()
        product_456 = "commons-client-4.5.6"
        product_459 = "commons-client-4.5.9"
        product_mix = [product_456, product_459]

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")

        handle_maven_del(
            test_zip, product_456,
            ignore_patterns=[".*.sha1"],
            buckets=[(None, TEST_BUCKET, None, None)],
            dir_=self.tempdir,
            do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]

        httpclient_ignored_files = [
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1"
        ]
        not_ignored = [e for e in COMMONS_CLIENT_456_FILES if e not in httpclient_ignored_files]
        not_ignored.extend(COMMONS_CLIENT_459_FILES)
        not_ignored.extend(
            [e for e in COMMONS_LOGGING_FILES if e not in httpclient_ignored_files])
        self.assertEqual(
            len(not_ignored) * 2 + COMMONS_CLIENT_META_NUM,
            len(actual_files)
        )

        for f in httpclient_ignored_files:
            self.assertIn(f, actual_files)
            self.check_product(f, [product_456])

        commons_logging_sha1_files = [
            "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1",
        ]
        for f in commons_logging_sha1_files:
            self.assertIn(f, actual_files)
            self.check_product(f, product_mix)

        non_sha1_files = [
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom",
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar",
        ]
        for f in non_sha1_files:
            self.assertNotIn(f, actual_files)

    def __test_prefix_deletion(self, prefix: str):
        self.__prepare_content(prefix)

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            buckets=[(None, TEST_BUCKET, prefix, None)],
            dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        # need to double mvn num because of .prodinfo files
        self.assertEqual(
            COMMONS_CLIENT_459_MVN_NUM * 2 + COMMONS_CLIENT_META_NUM,
            len(actual_files)
        )

        prefix_ = remove_prefix(prefix, "/")
        PREFIXED_COMMONS_CLIENT_456_FILES = [
            os.path.join(prefix_, f) for f in COMMONS_CLIENT_456_FILES]
        for f in PREFIXED_COMMONS_CLIENT_456_FILES:
            self.assertNotIn(f, actual_files)

        PREFIXED_COMMONS_CLIENT_METAS = [
            os.path.join(prefix_, f) for f in COMMONS_CLIENT_METAS]
        PREFIXED_COMMONS_LOGGING_FILES = [
            os.path.join(prefix_, f) for f in COMMONS_LOGGING_FILES]
        PREFIXED_COMMONS_LOGGING_METAS = [
            os.path.join(prefix_, f) for f in COMMONS_LOGGING_METAS]
        PREFIXED_ARCHE_CATALOG_FILES = [
            os.path.join(prefix_, f) for f in ARCHETYPE_CATALOG_FILES]
        file_set = [
            *PREFIXED_COMMONS_CLIENT_METAS, *PREFIXED_ARCHE_CATALOG_FILES,
            *PREFIXED_COMMONS_LOGGING_FILES, *PREFIXED_COMMONS_LOGGING_METAS
        ]
        for f in file_set:
            self.assertIn(f, actual_files)

        for obj in objs:
            if not obj.key.endswith(PROD_INFO_SUFFIX):
                self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
                self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        product_459 = "commons-client-4.5.9"
        meta_obj_client = test_bucket.Object(PREFIXED_COMMONS_CLIENT_METAS[0])
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<groupId>org.apache.httpcomponents</groupId>", meta_content_client
        )
        self.assertIn("<artifactId>httpclient</artifactId>", meta_content_client)
        self.assertNotIn("<version>4.5.6</version>", meta_content_client)
        self.assertNotIn("<latest>4.5.6</latest>", meta_content_client)
        self.assertNotIn("<release>4.5.6</release>", meta_content_client)
        self.assertIn("<latest>4.5.9</latest>", meta_content_client)
        self.assertIn("<release>4.5.9</release>", meta_content_client)
        self.assertIn("<version>4.5.9</version>", meta_content_client)

        PREFIXED_ARCHE_CATALOG = os.path.join(prefix_, ARCHETYPE_CATALOG)
        meta_obj_cat = test_bucket.Object(PREFIXED_ARCHE_CATALOG)
        meta_content_cat = str(meta_obj_cat.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<groupId>org.apache.httpcomponents</groupId>", meta_content_cat
        )
        self.assertIn("<artifactId>httpclient</artifactId>", meta_content_cat)
        self.assertNotIn("<version>4.5.6</version>", meta_content_cat)

        meta_obj_logging = test_bucket.Object(PREFIXED_COMMONS_LOGGING_METAS[0])
        self.assertNotIn(PRODUCT_META_KEY, meta_obj_logging.metadata)
        meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
        self.assertIn("<groupId>commons-logging</groupId>", meta_content_logging)
        self.assertIn("<artifactId>commons-logging</artifactId>", meta_content_logging)
        self.assertIn("<version>1.2</version>", meta_content_logging)
        self.assertIn("<latest>1.2</latest>", meta_content_logging)
        self.assertIn("<release>1.2</release>", meta_content_logging)

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        handle_maven_del(
            test_zip, product_459,
            buckets=[(None, TEST_BUCKET, prefix, None)],
            dir_=self.tempdir,
            do_index=False
        )

        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def __prepare_content(self, prefix=None):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            buckets=[(None, TEST_BUCKET, prefix, None)],
            dir_=self.tempdir,
            do_index=False
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            buckets=[(None, TEST_BUCKET, prefix, None)],
            dir_=self.tempdir,
            do_index=False
        )
