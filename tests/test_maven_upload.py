from mrrc.config import mrrc_config, AWS_ENDPOINT
from mrrc.pkgs.maven import handle_maven_uploading
from mrrc.storage.s3client import PRODUCT_META_KEY, CHECKSUM_META_KEY
from tests.base import BaseMRRCTest
from moto import mock_s3
from unittest.mock import MagicMock
import boto3
import os

TEST_BUCKET = "test_bucket"

COMMONS_CLIENT_456_FILES = [
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom",
]

COMMONS_CLIENT_459_FILES = [
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom.sha1",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar.sha1",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom",
]

COMMONS_CLIENT_META = "org/apache/httpcomponents/httpclient/maven-metadata.xml"

COMMONS_LOGGING_FILES = [
    "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar",
    "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.jar",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.pom",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1",
]

COMMONS_LOGGING_META = "commons-logging/commons-logging/maven-metadata.xml"


@mock_s3
class MavenUploadTest(BaseMRRCTest):
    def setUp(self):
        super().setUp()
        # mock_s3 is used to generate expected content
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET)

    def tearDown(self):
        bucket = self.mock_s3.Bucket(TEST_BUCKET)
        try:
            bucket.objects.all().delete()
            bucket.delete()
        except ValueError:
            pass
        super().tearDown()

    def __prepare_s3(self):
        conf = mrrc_config()
        aws_configs = conf.get_aws_configs()
        return boto3.resource(
            "s3",
            region_name=conf.get_aws_region(),
            aws_access_key_id=conf.get_aws_key_id(),
            aws_secret_access_key=conf.get_aws_key(),
            endpoint_url=aws_configs[AWS_ENDPOINT]
            if AWS_ENDPOINT in aws_configs
            else None,
        )

    def test_fresh_upload(self):
        conf = mrrc_config()
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(conf, test_zip, product, True, bucket_name=TEST_BUCKET)

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(12, len(objs))

        actual_files = [obj.key for obj in objs]

        for f in COMMONS_CLIENT_456_FILES:
            self.assertIn(f, actual_files)
        self.assertIn(COMMONS_CLIENT_META, actual_files)

        for f in COMMONS_LOGGING_FILES:
            self.assertIn(f, actual_files)
        self.assertIn(COMMONS_LOGGING_META, actual_files)

        for obj in objs:
            self.assertEqual(product, obj.Object().metadata[PRODUCT_META_KEY])
            self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
            self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        meta_obj_client = test_bucket.Object(COMMONS_CLIENT_META)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<groupId>org.apache.httpcomponents</groupId>", meta_content_client
        )
        self.assertIn("<artifactId>httpclient</artifactId>", meta_content_client)
        self.assertIn("<version>4.5.6</version>", meta_content_client)
        self.assertIn("<latest>4.5.6</latest>", meta_content_client)
        self.assertIn("<release>4.5.6</release>", meta_content_client)
        self.assertNotIn("<version>4.5.9</version>", meta_content_client)

        meta_obj_logging = test_bucket.Object(COMMONS_LOGGING_META)
        meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
        self.assertIn("<groupId>commons-logging</groupId>", meta_content_logging)
        self.assertIn("<artifactId>commons-logging</artifactId>", meta_content_logging)
        self.assertIn("<version>1.2</version>", meta_content_logging)
        self.assertIn("<latest>1.2</latest>", meta_content_logging)
        self.assertIn("<release>1.2</release>", meta_content_logging)

    def test_overlap_upload(self):
        conf = mrrc_config()
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            conf, test_zip, product_456, True, bucket_name=TEST_BUCKET
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            conf, test_zip, product_459, True, bucket_name=TEST_BUCKET
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(16, len(objs))

        actual_files = [obj.key for obj in objs]
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
        self.assertIn(COMMONS_CLIENT_META, actual_files)
        product_mix = set([product_456, product_459])
        self.assertSetEqual(
            product_mix,
            set(
                test_bucket.Object(COMMONS_CLIENT_META)
                .metadata[PRODUCT_META_KEY]
                .split(",")
            ),
        )

        for f in COMMONS_LOGGING_FILES:
            self.assertIn(f, actual_files)
            self.assertSetEqual(
                product_mix,
                set(test_bucket.Object(f).metadata[PRODUCT_META_KEY].split(",")),
            )
        self.assertIn(COMMONS_LOGGING_META, actual_files)
        self.assertSetEqual(
            product_mix,
            set(
                test_bucket.Object(COMMONS_LOGGING_META)
                .metadata[PRODUCT_META_KEY]
                .split(",")
            ),
        )

        meta_obj_client = test_bucket.Object(COMMONS_CLIENT_META)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<groupId>org.apache.httpcomponents</groupId>", meta_content_client
        )
        self.assertIn("<artifactId>httpclient</artifactId>", meta_content_client)
        self.assertIn("<latest>4.5.9</latest>", meta_content_client)
        self.assertIn("<release>4.5.9</release>", meta_content_client)
        self.assertIn("<version>4.5.6</version>", meta_content_client)
        self.assertIn("<version>4.5.9</version>", meta_content_client)

        meta_obj_logging = test_bucket.Object(COMMONS_LOGGING_META)
        meta_content_logging = str(meta_obj_logging.get()["Body"].read(), "utf-8")
        self.assertIn("<groupId>commons-logging</groupId>", meta_content_logging)
        self.assertIn("<artifactId>commons-logging</artifactId>", meta_content_logging)
        self.assertIn("<version>1.2</version>", meta_content_logging)
        self.assertIn("<latest>1.2</latest>", meta_content_logging)
        self.assertIn("<release>1.2</release>", meta_content_logging)

    def test_ignore_upload(self):
        conf = mrrc_config()
        conf.get_ignore_patterns = MagicMock(return_value=[".*.sha1"])
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            conf, test_zip, product_456, True, bucket_name=TEST_BUCKET
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(7, len(objs))

        actual_files = [obj.key for obj in objs]

        sha1_files = [
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
            "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1",
        ]

        for f in sha1_files:
            self.assertNotIn(f, actual_files)
