from charon.pkgs.maven import handle_maven_uploading
from charon.storage import PRODUCT_META_KEY, CHECKSUM_META_KEY
from charon.utils.strings import remove_prefix
from tests.base import BaseTest, SHORT_TEST_PREFIX, LONG_TEST_PREFIX
from moto import mock_s3
import boto3
import os

TEST_BUCKET = "test_bucket"

COMMONS_CLIENT_456_FILES = [
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom"
]

COMMONS_CLIENT_459_FILES = [
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom.sha1",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar.sha1",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom"
]

ARCHETYPE_CATALOG = "archetype-catalog.xml"
ARCHETYPE_CATALOG_FILES = [
    ARCHETYPE_CATALOG,
    "archetype-catalog.xml.sha1",
    "archetype-catalog.xml.md5",
    "archetype-catalog.xml.sha256"
]

COMMONS_CLIENT_META = "org/apache/httpcomponents/httpclient/maven-metadata.xml"
COMMONS_CLIENT_METAS = [
    COMMONS_CLIENT_META,
    "org/apache/httpcomponents/httpclient/maven-metadata.xml.sha1",
    "org/apache/httpcomponents/httpclient/maven-metadata.xml.md5",
    "org/apache/httpcomponents/httpclient/maven-metadata.xml.sha256"
]

COMMONS_LOGGING_FILES = [
    "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar",
    "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.jar",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.pom",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1",
]

COMMONS_LOGGING_META = "commons-logging/commons-logging/maven-metadata.xml"
COMMONS_LOGGING_METAS = [
    COMMONS_LOGGING_META,
    "commons-logging/commons-logging/maven-metadata.xml.sha1",
    "commons-logging/commons-logging/maven-metadata.xml.md5",
    "commons-logging/commons-logging/maven-metadata.xml.sha256"
]

NON_MVN_FILES = [
    "commons-client-4.5.6/example-settings.xml",
    "commons-client-4.5.6/licenses/gnu",
    "commons-client-4.5.6/licenses/licenses.txt",
    "commons-client-4.5.6/README.md",
    "commons-client-4.5.9/example-settings.xml",
    "commons-client-4.5.9/licenses/gnu",
    "commons-client-4.5.9/licenses/licenses.txt",
    "commons-client-4.5.9/README.md"
]


@mock_s3
class MavenUploadTest(BaseTest):
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
        return boto3.resource('s3')

    def test_fresh_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        # self.assertEqual(12, len(objs))

        actual_files = [obj.key for obj in objs]

        filesets = [
            COMMONS_CLIENT_METAS, COMMONS_CLIENT_456_FILES,
            COMMONS_LOGGING_FILES, COMMONS_LOGGING_METAS,
            ARCHETYPE_CATALOG_FILES
        ]

        for fileset in filesets:
            for f in fileset:
                self.assertIn(f, actual_files)

        for f in NON_MVN_FILES:
            self.assertNotIn(f, actual_files)

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

        catalog = test_bucket.Object(ARCHETYPE_CATALOG)
        cat_content = str(catalog.get()["Body"].read(), "utf-8")
        self.assertIn("<version>4.5.6</version>", cat_content)
        self.assertIn("<artifactId>httpclient</artifactId>", cat_content)
        self.assertIn("<groupId>org.apache.httpcomponents</groupId>", cat_content)

    def test_overlap_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            bucket_name=TEST_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        # self.assertEqual(16, len(objs))

        actual_files = [obj.key for obj in objs]

        filesets = [
            COMMONS_CLIENT_METAS, COMMONS_CLIENT_456_FILES,
            COMMONS_CLIENT_459_FILES,
            ARCHETYPE_CATALOG_FILES
        ]

        for fileset in filesets:
            for f in fileset:
                self.assertIn(f, actual_files)

        self.assertIn(COMMONS_CLIENT_META, actual_files)
        product_mix = {product_456, product_459}
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

        catalog = test_bucket.Object(ARCHETYPE_CATALOG)
        cat_content = str(catalog.get()["Body"].read(), "utf-8")
        self.assertIn("<version>4.5.6</version>", cat_content)
        self.assertIn("<version>4.5.9</version>", cat_content)
        self.assertIn("<artifactId>httpclient</artifactId>", cat_content)
        self.assertIn("<groupId>org.apache.httpcomponents</groupId>", cat_content)

    def test_ignore_upload(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456, [".*.sha1"],
            bucket_name=TEST_BUCKET, dir_=self.tempdir, do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        # self.assertEqual(7, len(objs))

        actual_files = [obj.key for obj in objs]

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
            bucket_name=TEST_BUCKET,
            prefix=prefix,
            dir_=self.tempdir,
            do_index=False
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]
        # self.assertEqual(12, len(actual_files))

        prefix_ = remove_prefix(prefix, "/")
        PREFIXED_COMMONS_CLIENT_456_FILES = [
            os.path.join(prefix_, f) for f in COMMONS_CLIENT_456_FILES]
        for f in PREFIXED_COMMONS_CLIENT_456_FILES:
            self.assertIn(f, actual_files)
        PREFIXED_COMMONS_CLIENT_META = os.path.join(prefix_, COMMONS_CLIENT_META)
        self.assertIn(PREFIXED_COMMONS_CLIENT_META, actual_files)

        PREFIXED_COMMONS_LOGGING_FILES = [
            os.path.join(prefix_, f) for f in COMMONS_LOGGING_FILES]
        for f in PREFIXED_COMMONS_LOGGING_FILES:
            self.assertIn(f, actual_files)
        PREFIXED_COMMONS_LOGGING_META = os.path.join(prefix_, COMMONS_LOGGING_META)
        self.assertIn(PREFIXED_COMMONS_LOGGING_META, actual_files)

        PREFIXED_NON_MVN_FILES = [
            os.path.join(prefix_, f) for f in NON_MVN_FILES]
        for f in PREFIXED_NON_MVN_FILES:
            self.assertNotIn(f, actual_files)

        for obj in objs:
            self.assertEqual(product, obj.Object().metadata[PRODUCT_META_KEY])
            self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
            self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        meta_obj_client = test_bucket.Object(PREFIXED_COMMONS_CLIENT_META)
        self.assertIsNotNone(meta_obj_client)

        meta_obj_logging = test_bucket.Object(PREFIXED_COMMONS_LOGGING_META)
        self.assertIsNotNone(meta_obj_logging)
