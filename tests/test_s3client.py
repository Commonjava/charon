from mrrc.s3client import S3Client, PRODUCT_META_KEY, CHECKSUM_META_KEY
from mrrc.util import write_file, read_sha1
from tests.base import BaseMRRCTest
from mrrc.config import mrrc_config, AWS_ENDPOINT
from mrrc.archive import extract_zip_all
import boto3
from moto import mock_s3
import os
import zipfile
import shutil

MY_BUCKET = "my_bucket"
MY_PREFIX = "mock_folder"

@mock_s3
class S3ClientTest(BaseMRRCTest):
    def setUp(self):
        super().setUp()
        # mock_s3 is used to generate expected content
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=MY_BUCKET)
        # s3_client is the client we will test
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
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        bucket.put_object(Key='org/foo/bar/1.0/foo-bar-1.0.pom', Body='test content pom')
        bucket.put_object(Key='org/foo/bar/1.0/foo-bar-1.0.jar', Body='test content jar')
        bucket.put_object(Key='org/x/y/1.0/x-y-1.0.pom', Body='test content pom')
        bucket.put_object(Key='org/x/y/1.0/x-y-1.0.jar', Body='test content jar')
        
        files = self.s3_client.get_files(bucket_name=MY_BUCKET)
        self.assertEqual(4, len(files))
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.pom', files)
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.jar', files)
        self.assertIn('org/x/y/1.0/x-y-1.0.pom', files)
        self.assertIn('org/x/y/1.0/x-y-1.0.jar', files)
        
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,suffix='.pom')
        self.assertEqual(2, len(files))
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.pom', files)
        self.assertNotIn('org/foo/bar/1.0/foo-bar-1.0.jar', files)
        self.assertIn('org/x/y/1.0/x-y-1.0.pom', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.jar', files)
        
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,prefix='org/foo/bar')
        self.assertEqual(2, len(files))
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.pom', files)
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.jar', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.pom', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.jar', files)
        
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,prefix='org/foo/bar',suffix='.pom')
        self.assertEqual(1, len(files))
        self.assertIn('org/foo/bar/1.0/foo-bar-1.0.pom', files)
        self.assertNotIn('org/foo/bar/1.0/foo-bar-1.0.jar', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.pom', files)
        self.assertNotIn('org/x/y/1.0/x-y-1.0.jar', files)

    def test_upload_and_delete_files(self):
        zip = zipfile.ZipFile(os.path.join(os.getcwd(),'tests-input/commons-lang3.zip'))
        temp_root = os.path.join(self.tempdir, 'tmp_zip')
        os.mkdir(temp_root)
        extract_zip_all(zip, temp_root)
        root = os.path.join(temp_root, 'apache-commons-maven-repository/maven-repository')
        all_files = []
        for (dir,_,names) in os.walk(temp_root):
            all_files.extend([os.path.join(dir,n) for n in names])
        
        # First, test upload without any products
        self.s3_client.upload_files(all_files, bucket_name=MY_BUCKET, root=root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(26, len(objects))
        
        # Second, test upload existed files with the product. The product will be added to metadata    
        self.s3_client.upload_files(all_files, bucket_name=MY_BUCKET, product="apache-commons", root=root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(26, len(objects))
        for obj in objects:
            self.assertEqual("apache-commons",obj.Object().metadata[PRODUCT_META_KEY])
            self.assertNotEqual("",obj.Object().metadata[CHECKSUM_META_KEY])
        
        # Third, test upload existed files with extra product. The extra product will be added to metadata   
        self.s3_client.upload_files(all_files, bucket_name=MY_BUCKET, product="commons-lang3", root=root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(26, len(objects))
        for obj in objects:
            self.assertEqual("apache-commons,commons-lang3",obj.Object().metadata["rh-products"])
            self.assertNotEqual("",obj.Object().metadata[CHECKSUM_META_KEY])
        
        # Fourth, test delete files without product. The file will not be deleted and no product metadata will be changed.
        self.s3_client.delete_files(all_files, bucket_name=MY_BUCKET, root=root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(26, len(objects))
        for obj in objects:
            self.assertEqual("apache-commons,commons-lang3",obj.Object().metadata["rh-products"])
            self.assertNotEqual("",obj.Object().metadata[CHECKSUM_META_KEY])
        
        # Fifth, test delete files with one prodct. The file will not be deleted, but the product will be removed from metadata.
        self.s3_client.delete_files(all_files, bucket_name=MY_BUCKET, product="apache-commons", root=root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(26, len(objects))
        for obj in objects:
            self.assertEqual("commons-lang3",obj.Object().metadata["rh-products"])
            self.assertNotEqual("",obj.Object().metadata[CHECKSUM_META_KEY])
        
        # Finally, test delete files with left prodct. The file will be deleted, because all products have been removed from metadata.
        self.s3_client.delete_files(all_files, bucket_name=MY_BUCKET, product="commons-lang3", root=root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        self.assertEqual(0, len(list(bucket.objects.all())))
        
        shutil.rmtree(temp_root)
        
    def test_upload_with_checksum(self):
        temp_root = os.path.join(self.tempdir, 'tmp_upd')
        os.mkdir(temp_root)
        path = "org/foo/bar/1.0"
        os.makedirs(os.path.join(temp_root, path))
        file = os.path.join(temp_root, path, "foo-bar-1.0.txt")
        
        content = "This is foo bar 1.0 1"
        write_file(file, content)
        sha1_1 = read_sha1(file)
        self.s3_client.upload_files([file], bucket_name=MY_BUCKET, product="foo-bar-1.0", root=temp_root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(1, len(objects))
        obj = objects[0]
        self.assertEqual("foo-bar-1.0",obj.Object().metadata[PRODUCT_META_KEY])
        self.assertEqual(sha1_1,obj.Object().metadata[CHECKSUM_META_KEY])
        
        os.remove(file)
        
        content = "This is foo bar 1.0 2"
        write_file(file, content)
        sha1_2 = read_sha1(file)
        self.assertNotEqual(sha1_1, sha1_2)
        self.s3_client.upload_files([file], bucket_name=MY_BUCKET, product="foo-bar-1.0-2", root=temp_root)
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        objects = list(bucket.objects.all())
        self.assertEqual(1, len(objects))
        obj = objects[0]
        self.assertEqual("foo-bar-1.0",obj.Object().metadata[PRODUCT_META_KEY])
        self.assertEqual(sha1_1,obj.Object().metadata[CHECKSUM_META_KEY])
        
        shutil.rmtree(temp_root)