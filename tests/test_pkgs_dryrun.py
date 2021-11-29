from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from tests.base import BaseTest
from moto import mock_s3
import boto3
import os

TEST_BUCKET = "test_bucket"


@mock_s3
class PkgsDryRunTest(BaseTest):
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

    def test_maven_upload_dry_run(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def test_maven_delete_dry_run(self):
        self.__prepare_maven_content()

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(26, len(objs))

    def test_npm_upload_dry_run(self):
        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(0, len(objs))

    def test_npm_deletion_dry_run(self):
        self.__prepare_npm_content()

        test_tgz = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_del(
            test_tgz, product_7_14_5,
            bucket_name=TEST_BUCKET,
            dir_=self.tempdir,
            dry_run=True
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        self.assertEqual(11, len(objs))

    def __prepare_maven_content(self):
        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

        test_zip = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            test_zip, product_459,
            bucket_name=TEST_BUCKET, dir_=self.tempdir
        )

    def __prepare_npm_content(self):
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
