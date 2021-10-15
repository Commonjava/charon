from mrrc.pkgs.npm import handle_npm_uploading
from mrrc.storage import PRODUCT_META_KEY, CHECKSUM_META_KEY
from tests.base import BaseMRRCTest
from moto import mock_s3
import boto3
import os

TEST_BUCKET = "npm_bucket"

CODE_FRAME_7_14_5_FILES = [
    "@babel/code-frame/7.14.5/package.json",
    "@babel/code-frame/-/code-frame-7.14.5.tgz",
]

CODE_FRAME_7_15_8_FILES = [
    "@babel/code-frame/7.15.8/package.json",
    "@babel/code-frame/-/code-frame-7.15.8.tgz",
]

CODE_FRAME_META = "@babel/code-frame/package.json"


@mock_s3
class NPMUploadTest(BaseMRRCTest):
    def setUp(self):
        super().setUp()
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
        return boto3.resource("s3")

    def test_npm_upload(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(3, len(objs))

        actual_files = [obj.key for obj in objs]

        for f in CODE_FRAME_7_14_5_FILES:
            self.assertIn(f, actual_files)
        self.assertIn(CODE_FRAME_META, actual_files)

        for obj in objs:
            self.assertEqual(product_7_14_5, obj.Object().metadata[PRODUCT_META_KEY])
            self.assertIn(CHECKSUM_META_KEY, obj.Object().metadata)
            self.assertNotEqual("", obj.Object().metadata[CHECKSUM_META_KEY].strip())

        meta_obj_client = test_bucket.Object(CODE_FRAME_META)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@babel/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": \"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {\"7.14.5\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertIn("\"dist_tags\": {\"latest\": \"7.14.5\"}", meta_content_client)

    def test_double_uploads(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.15.8.tgz")
        product_7_15_8 = "code-frame-7.15.8"
        handle_npm_uploading(
            test_tgz, product_7_15_8, bucket_name=TEST_BUCKET, dir_=self.tempdir
        )
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(5, len(objs))

        actual_files = [obj.key for obj in objs]

        for f in CODE_FRAME_7_14_5_FILES:
            self.assertIn(f, actual_files)
            self.assertEqual(
                product_7_14_5, test_bucket.Object(f).metadata[PRODUCT_META_KEY]
            )
        for f in CODE_FRAME_7_15_8_FILES:
            self.assertIn(f, actual_files)
            self.assertEqual(
                product_7_15_8, test_bucket.Object(f).metadata[PRODUCT_META_KEY]
            )
        self.assertIn(CODE_FRAME_META, actual_files)
        product_mix = set([product_7_14_5, product_7_15_8])
        self.assertSetEqual(
            product_mix,
            set(
                test_bucket.Object(CODE_FRAME_META)
                .metadata[PRODUCT_META_KEY]
                .split(",")
            ),
        )

        meta_obj_client = test_bucket.Object(CODE_FRAME_META)
        meta_content_client = str(meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"name\": \"@babel/code-frame\"", meta_content_client)
        self.assertIn("\"description\": \"Generate errors that contain a code frame that point to source locations.\"", meta_content_client)
        self.assertIn("\"repository\": {\"type\": \"git\", \"url\": \"https://github.com/babel/babel.git\"", meta_content_client)
        self.assertIn("\"version\": \"7.15.8\"", meta_content_client)
        self.assertIn("\"version\": \"7.14.5\"", meta_content_client)
        self.assertIn("\"versions\": {", meta_content_client)
        self.assertIn("\"7.15.8\": {\"name\":", meta_content_client)
        self.assertIn("\"7.14.5\": {\"name\":", meta_content_client)
        self.assertIn("\"license\": \"MIT\"", meta_content_client)
        self.assertIn("\"dist_tags\": {\"latest\": \"7.15.8\"}", meta_content_client)