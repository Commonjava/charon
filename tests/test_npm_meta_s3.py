import os

import boto3
from moto import mock_s3

from mrrc.config import mrrc_config, AWS_ENDPOINT
from mrrc.pkgs.npm import store_package_metadata_to_S3, read_package_metadata_from_content
from mrrc.storage.s3client import S3Client
from tests.base import BaseMRRCTest

MY_BUCKET = "npm_bucket"


@mock_s3
class NPMMetadataTest(BaseMRRCTest):
    def setUp(self):
        super().setUp()
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=MY_BUCKET)
        self.s3_client = S3Client()

    def tearDown(self):
        s3 = self.__prepare_s3()
        bucket = s3.Bucket(MY_BUCKET)
        bucket.objects.all().delete()
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

    def test_store_package_metadata_to_S3_for_old_version(self):
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        original_old_version_package_json = \
            "{\"name\": \"@redhat/kogito-tooling-workspace\", \"dist_tags\": {\"latest\": " \
            "\"0.5.8\"}," \
            "\"versions\": {\"0.5.8\": {\"name\": \"@redhat/kogito-tooling-workspace\", " \
            "\"version\": \"0.5.8\", \"title\": \"0.5.8title\", \"description\": " \
            "\"0.5.8description\", " \
            "\"keywords\": [\"0.5.8\"], \"maintainers\": [\"0.5.8maintainer\"], " \
            "\"repository\": {\"type\": \"git\", \"url\": \"https://github.com/0.5.8.git\"}, " \
            "\"bugs\": \"0.5.8bugs\", \"license\": \"Apache-2.0.1\", " \
            "\"dependencies\": {\"@redhat/kogito-tooling-channel-common-api\": \"^0.5.8\"}}}, " \
            "\"maintainers\": [\"0.5.8maintainer\"], \"description\": \"0.5.8 description\", " \
            "\"time\": {}, \"author\": \"0.5.8author\", \"users\": {\"0.5.8users\": true}, " \
            "\"repository\": {\"type\": \"git\", \"url\": \"https://github.com/0.5.8.git\"}, " \
            "\"readme\": \"0.5.8readme\", \"readmeFilename\": \"0.5.8readmeFilename\", " \
            "\"homepage\": \"0.5.8homepage\", " \
            "\"keywords\": [\"0.5.8\"], \"bugs\": \"0.5.8bugs\", \"license\": \"Apache-2.0.1\"}"

        bucket.put_object(Key='@redhat/kogito-tooling-workspace/package.json',
                          Body=str(original_old_version_package_json))
        temp_root = os.path.join(self.tempdir, 'tmp_tgz')
        os.mkdir(temp_root)
        tarball_test_path = os.path.join(os.getcwd(),
                                         'tests/input/kogito-tooling-workspace-0.9.0-3.tgz')
        store_package_metadata_to_S3(self.s3_client, tarball_test_path, temp_root, MY_BUCKET,
                                     "kogito-tooling-workspace-0.9.0-3")
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,
                                         prefix='@redhat/kogito-tooling-workspace',
                                         suffix='package.json')
        self.assertEqual(1, len(files))
        self.assertIn('@redhat/kogito-tooling-workspace/package.json', files)

        content = self.s3_client.read_file_content(MY_BUCKET,
                                                   '@redhat/kogito-tooling-workspace/package.json')
        merged = read_package_metadata_from_content(content)
        self.assertEqual("@redhat/kogito-tooling-workspace", merged.name)
        self.assertEqual(2, len(merged.versions))
        self.assertIn("0.5.8", merged.versions.keys())
        self.assertIn("0.9.0-3", merged.versions.keys())
        self.assertEqual("0.9.0-3", merged.dist_tags["latest"])
        self.assertIn("0.5.8maintainer", merged.maintainers)
        self.assertIn("0.5.8users", merged.users.keys())
        self.assertEqual("https://github.com/kiegroup/kogito-tooling.git", merged.repository["url"])
        self.assertEqual("0.5.8homepage", merged.homepage)
        self.assertIn("0.5.8", merged.keywords)
        self.assertEqual("0.5.8bugs", merged.bugs)
        self.assertEqual("Apache-2.0", merged.license)

    def test_store_package_metadata_to_S3_for_new_version(self):
        bucket = self.mock_s3.Bucket(MY_BUCKET)
        original_new_version_package_json = \
            "{\"name\": \"@redhat/kogito-tooling-workspace\", \"dist_tags\": {\"latest\": " \
            "\"1.0.1\"}," \
            "\"versions\": {\"1.0.1\": {\"name\": \"@redhat/kogito-tooling-workspace\", " \
            "\"version\": \"1.0.1\", \"title\": \"1.0.1title\", \"description\": " \
            "\"1.0.1description\", " \
            "\"keywords\": [\"1.0.1\"], \"maintainers\": [\"1.0.1maintainer\"], " \
            "\"repository\": {\"type\": \"git\", \"url\": \"https://github.com/1.0.1.git\"}, " \
            "\"bugs\": \"1.0.1bugs\", \"license\": \"Apache-2.0.1\", " \
            "\"dependencies\": {\"@redhat/kogito-tooling-channel-common-api\": \"^1.0.1\"}}}, " \
            "\"maintainers\": [\"1.0.1maintainer\"], \"description\": \"1.0.1 description\", " \
            "\"time\": {}, \"author\": \"1.0.1author\", \"users\": {\"1.0.1users\": true}, " \
            "\"repository\": {\"type\": \"git\", \"url\": \"https://github.com/1.0.1.git\"}, " \
            "\"readme\": \"1.0.1readme\", \"readmeFilename\": \"1.0.1readmeFilename\", " \
            "\"homepage\": \"1.0.1homepage\", " \
            "\"keywords\": [\"1.0.1\"], \"bugs\": \"1.0.1bugs\", \"license\": \"Apache-2.0.1\"}"

        bucket.put_object(Key='@redhat/kogito-tooling-workspace/package.json',
                          Body=str(original_new_version_package_json))
        temp_root = os.path.join(self.tempdir, 'tmp_tgz')
        os.mkdir(temp_root)
        tarball_test_path = os.path.join(os.getcwd(),
                                         'tests/input/kogito-tooling-workspace-0.9.0-3.tgz')
        store_package_metadata_to_S3(self.s3_client, tarball_test_path, temp_root, MY_BUCKET,
                                     "kogito-tooling-workspace-0.9.0-3")
        files = self.s3_client.get_files(bucket_name=MY_BUCKET,
                                         prefix='@redhat/kogito-tooling-workspace',
                                         suffix='package.json')
        self.assertEqual(1, len(files))
        self.assertIn('@redhat/kogito-tooling-workspace/package.json', files)

        content = self.s3_client.read_file_content(MY_BUCKET,
                                                   '@redhat/kogito-tooling-workspace/package.json')
        merged = read_package_metadata_from_content(content)
        self.assertEqual("@redhat/kogito-tooling-workspace", merged.name)
        self.assertEqual(2, len(merged.versions))
        self.assertIn("1.0.1", merged.versions.keys())
        self.assertIn("0.9.0-3", merged.versions.keys())
        self.assertEqual("1.0.1", merged.dist_tags["latest"])
        self.assertIn("1.0.1maintainer", merged.maintainers)
        self.assertIn("1.0.1users", merged.users.keys())
        self.assertEqual("https://github.com/1.0.1.git", merged.repository["url"])
        self.assertEqual("1.0.1homepage", merged.homepage)
        self.assertIn("1.0.1", merged.keywords)
        self.assertEqual("1.0.1bugs", merged.bugs)
        self.assertEqual("Apache-2.0.1", merged.license)
