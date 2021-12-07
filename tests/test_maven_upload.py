from charon.pkgs.maven import handle_maven_uploading
from charon.pkgs.pkg_utils import is_metadata
from charon.storage import PRODUCT_META_KEY, CHECKSUM_META_KEY
from charon.utils.strings import remove_prefix
from tests.base import BaseTest, SHORT_TEST_PREFIX, LONG_TEST_PREFIX
from tests.commons import (
    TEST_MVN_BUCKET, COMMONS_CLIENT_456_FILES, COMMONS_CLIENT_459_FILES,
    COMMONS_CLIENT_METAS, COMMONS_LOGGING_FILES, COMMONS_LOGGING_METAS,
    NON_MVN_FILES
)
from moto import mock_s3
import boto3
import os


@mock_s3
class MavenUploadTest(BaseTest):
    def setUp(self):
        super().setUp()
        # mock_s3 is used to generate expected content
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=TEST_MVN_BUCKET)

    def tearDown(self):
        bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        try:
            bucket.objects.all().delete()
            bucket.delete()
        except ValueError:
            pass
        super().tearDown()

    def __prepare_s3(self):
        return boto3.resource('s3')

    def test_fresh_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_MVN_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(18, len(actual_files))

        for f in COMMONS_CLIENT_456_FILES:
            self.assertIn(f, actual_files)
        for f in COMMONS_CLIENT_METAS:
            self.assertIn(f, actual_files)

        for f in COMMONS_LOGGING_FILES:
            self.assertIn(f, actual_files)
        for f in COMMONS_LOGGING_METAS:
            self.assertIn(f, actual_files)

        for f in NON_MVN_FILES:
            self.assertNotIn(f, actual_files)

        for obj in objs:
            file_obj = obj.Object()
            if not is_metadata(file_obj.key):
                self.assertEqual(product, file_obj.metadata[PRODUCT_META_KEY])
            else:
                self.assertNotIn(PRODUCT_META_KEY, file_obj.metadata)
                if file_obj.key.endswith("maven-metadata.xml"):
                    sha1_checksum = file_obj.metadata[CHECKSUM_META_KEY].strip()
                    sha1_obj = test_bucket.Object(file_obj.key+".sha1")
                    sha1_file_content = str(sha1_obj.get()['Body'].read(), 'utf-8')
                    self.assertEqual(sha1_checksum, sha1_file_content)
            self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
            self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        meta_obj_client = test_bucket.Object(COMMONS_CLIENT_METAS[0])
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<groupId>org.apache.httpcomponents</groupId>", meta_content_client
        )
        self.assertIn("<artifactId>httpclient</artifactId>", meta_content_client)
        self.assertIn("<version>4.5.6</version>", meta_content_client)
        self.assertIn("<latest>4.5.6</latest>", meta_content_client)
        self.assertIn("<release>4.5.6</release>", meta_content_client)
        self.assertNotIn("<version>4.5.9</version>", meta_content_client)

        meta_obj_logging = test_bucket.Object(COMMONS_LOGGING_METAS[0])
        meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
        self.assertIn("<groupId>commons-logging</groupId>", meta_content_logging)
        self.assertIn("<artifactId>commons-logging</artifactId>", meta_content_logging)
        self.assertIn("<version>1.2</version>", meta_content_logging)
        self.assertIn("<latest>1.2</latest>", meta_content_logging)
        self.assertIn("<release>1.2</release>", meta_content_logging)

    def test_overlap_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            bucket_name=TEST_MVN_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_MVN_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(22, len(actual_files))

        for f in COMMONS_CLIENT_456_FILES:
            self.assertIn(f, actual_files)
            self.assertEqual(
                product_456, test_bucket.Object(f).metadata[PRODUCT_META_KEY]
            )
        for f in COMMONS_CLIENT_459_FILES:
            self.assertIn(f, actual_files)
            self.assertEqual(
                product_459, test_bucket.Object(f).metadata[PRODUCT_META_KEY]
            )
        for f in COMMONS_CLIENT_METAS:
            self.assertIn(f, actual_files)
        product_mix = set([product_456, product_459])

        for f in COMMONS_LOGGING_FILES:
            self.assertIn(f, actual_files)
            self.assertSetEqual(
                product_mix,
                set(test_bucket.Object(f).metadata[PRODUCT_META_KEY].split(",")),
            )
        for f in COMMONS_LOGGING_METAS:
            self.assertIn(f, actual_files)

        meta_obj_client = test_bucket.Object(COMMONS_CLIENT_METAS[0])
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<groupId>org.apache.httpcomponents</groupId>", meta_content_client
        )
        self.assertIn("<artifactId>httpclient</artifactId>", meta_content_client)
        self.assertIn("<latest>4.5.9</latest>", meta_content_client)
        self.assertIn("<release>4.5.9</release>", meta_content_client)
        self.assertIn("<version>4.5.6</version>", meta_content_client)
        self.assertIn("<version>4.5.9</version>", meta_content_client)

        meta_obj_logging = test_bucket.Object(COMMONS_LOGGING_METAS[0])
        meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
        self.assertIn("<groupId>commons-logging</groupId>", meta_content_logging)
        self.assertIn("<artifactId>commons-logging</artifactId>", meta_content_logging)
        self.assertIn("<version>1.2</version>", meta_content_logging)
        self.assertIn("<latest>1.2</latest>", meta_content_logging)
        self.assertIn("<release>1.2</release>", meta_content_logging)

    def test_ignore_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456, [".*.sha1"],
            bucket_name=TEST_MVN_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(13, len(actual_files))

        ignored_files = [
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1"
        ]

        for f in ignored_files:
            self.assertNotIn(f, actual_files)

    def test_short_prefix_upload(self):
        self.__test_prefix_upload(SHORT_TEST_PREFIX)

    def test_long_prefix_upload(self):
        self.__test_prefix_upload(LONG_TEST_PREFIX)

    def test_root_prefix_upload(self):
        self.__test_prefix_upload("/")

    def __test_prefix_upload(self, prefix: str):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_MVN_BUCKET,
            prefix=prefix,
            dir_=self.tempdir,
            do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_MVN_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        self.assertEqual(18, len(actual_files))

        prefix_ = remove_prefix(prefix, "/")
        PREFIXED_COMMONS_CLIENT_456_FILES = [
            os.path.join(prefix_, f) for f in COMMONS_CLIENT_456_FILES]
        for f in PREFIXED_COMMONS_CLIENT_456_FILES:
            self.assertIn(f, actual_files)
        PREFIXED_COMMONS_CLIENT_METAS = [
            os.path.join(prefix_, f) for f in COMMONS_CLIENT_METAS]
        for f in PREFIXED_COMMONS_CLIENT_METAS:
            self.assertIn(f, actual_files)

        PREFIXED_COMMONS_LOGGING_FILES = [
            os.path.join(prefix_, f) for f in COMMONS_LOGGING_FILES]
        for f in PREFIXED_COMMONS_LOGGING_FILES:
            self.assertIn(f, actual_files)
        PREFIXED_COMMONS_LOGGING_METAS = [
            os.path.join(prefix_, f) for f in COMMONS_LOGGING_METAS]
        for f in PREFIXED_COMMONS_LOGGING_METAS:
            self.assertIn(f, actual_files)

        PREFIXED_NON_MVN_FILES = [
            os.path.join(prefix_, f) for f in NON_MVN_FILES]
        for f in PREFIXED_NON_MVN_FILES:
            self.assertNotIn(f, actual_files)

        for obj in objs:
            file_obj = obj.Object()
            if not is_metadata(file_obj.key):
                self.assertEqual(product, file_obj.metadata[PRODUCT_META_KEY])
            else:
                self.assertNotIn(PRODUCT_META_KEY, file_obj.metadata)
            self.assertIn(CHECKSUM_META_KEY, file_obj.metadata)
            self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip())

        meta_obj_client = test_bucket.Object(PREFIXED_COMMONS_CLIENT_METAS[0])
        self.assertIsNotNone(meta_obj_client)

        meta_obj_logging = test_bucket.Object(PREFIXED_COMMONS_LOGGING_METAS[0])
        self.assertIsNotNone(meta_obj_logging)
