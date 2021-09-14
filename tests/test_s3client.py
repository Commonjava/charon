from mrrc.s3client import S3Client
from tests.base import BaseMRRCTest
from mrrc.config import mrrc_config, AWS_ENDPOINT
import boto3
import botocore
from moto import mock_s3
import os
import tempfile

MY_BUCKET = "my_bucket"
MY_PREFIX = "mock_folder"

@mock_s3
class S3ClientTest(BaseMRRCTest):
    def setUp(self):
        super().setUp()
        self.s3 = self.__prepare_s3()
        self.s3.create_bucket(Bucket=MY_BUCKET)
        self.s3_client = S3Client()
        
    def tearDown(self):
        s3 = self.__prepare_s3()
        bucket = s3.Bucket(MY_BUCKET)
        try:
            for key in bucket.objects.all():
                key.delete()
            bucket.delete()
        except:
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
            endpoint_url=aws_configs[AWS_ENDPOINT] if AWS_ENDPOINT in aws_configs else None
            )
        
    def test_get_files(self):
        bucket = self.s3.Bucket(MY_BUCKET)
        bucket.put_object(Key='org/foo/bar/1.0/foo-bar-1.0.pom', Body='test content pom')
        bucket.put_object(Key='org/foo/bar/1.0/foo-bar-1.0.jar', Body='test content jar')
        bucket.put_object(Key='org/x/y/1.0/x-y-1.0.pom', Body='test content pom')
        bucket.put_object(Key='org/x/y/1.0/x-y-1.0.jar', Body='test content jar')
        
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,suffix='.pom')
        self.assertEqual(2, len(files))
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.pom', files)
        self.assertNotIn('org/foo/bar/1.0/foo-bar-1.0.jar', files)
        
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,prefix='org/foo/bar')
        self.assertEqual(2, len(files))
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.pom', files)
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.jar', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.pom', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.jar', files)

