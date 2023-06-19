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
import unittest
import tempfile
import os
import shutil
import boto3
from typing import List
from charon.utils.files import overwrite_file
from charon.config import CONFIG_FILE
from charon.constants import PROD_INFO_SUFFIX
from charon.pkgs.pkg_utils import is_metadata
from charon.storage import PRODUCT_META_KEY, CHECKSUM_META_KEY
from tests.commons import TEST_BUCKET, TEST_MANIFEST_BUCKET
from moto import mock_s3

from tests.constants import HERE

SHORT_TEST_PREFIX = "ga"
LONG_TEST_PREFIX = "earlyaccess/all"


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.change_home()
        config_base = self.get_config_base()
        self.__prepare_template(config_base)
        default_config_content = """
ignore_patterns:
    - ".*^(redhat).*"
    - ".*snapshot.*"

ignore_signature_suffix:
  maven:
    - ".sha1"
    - ".sha256"
    - ".md5"
    - "maven-metadata.xml"
    - "archtype-catalog.xml"
  npm:
    - "package.json"

detach_signature_command: "touch {{ file }}.asc"

targets:
    ga:
    - bucket: "charon-test"
      prefix: ga
    ea:
    - bucket: "charon-test-ea"
      prefix: earlyaccess/all

    npm:
    - bucket: "charon-test-npm"
      registry: "npm1.registry.redhat.com"
aws_profile: "test"
manifest_bucket: "manifest"
      """
        self.prepare_config(config_base, default_config_content)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ

    def change_home(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='charon-test-')
        # Configure environment and copy templates
        os.environ['HOME'] = self.tempdir

    def __prepare_template(self, config_base):
        template_path = os.path.join(config_base, 'template')
        os.mkdir(config_base)
        shutil.copytree(os.path.join(HERE, "../template"), template_path)
        if not os.path.isdir(template_path):
            self.fail("Template initilization failed!")

    def prepare_config(self, config_base, file_content):
        config_path = os.path.join(config_base, CONFIG_FILE)
        overwrite_file(config_path, file_content)
        if not os.path.isfile(config_path):
            self.fail("Configuration initilization failed!")

    def get_temp_dir(self) -> str:
        return self.tempdir

    def get_config_base(self) -> str:
        return os.path.join(self.get_temp_dir(), '.charon')


@mock_s3
class PackageBaseTest(BaseTest):
    def setUp(self):
        super().setUp()
        # mock_s3 is used to generate expected content
        self.mock_s3 = self.__prepare_s3()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET)
        self.mock_s3.create_bucket(Bucket=TEST_MANIFEST_BUCKET)
        self.test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        self.test_manifest_bucket = self.mock_s3.Bucket(TEST_MANIFEST_BUCKET)

    def tearDown(self):
        buckets = [TEST_BUCKET, TEST_MANIFEST_BUCKET]
        self.cleanBuckets(buckets)
        super().tearDown()

    def cleanBuckets(self, buckets: List[str]):
        try:
            for bucket_ in buckets:
                bucket = self.mock_s3.Bucket(bucket_)
                bucket.objects.all().delete()
                bucket.delete()
        except ValueError:
            pass

    def __prepare_s3(self):
        return boto3.resource('s3')

    def check_product(self, file: str, prods: List[str], bucket=None, msg=None):
        prod_file = file + PROD_INFO_SUFFIX
        test_bucket = bucket
        if not test_bucket:
            test_bucket = self.test_bucket
        prod_f_obj = test_bucket.Object(prod_file)
        content = str(prod_f_obj.get()['Body'].read(), 'utf-8')
        self.assertEqual(
            set(prods),
            set([f for f in content.split("\n") if f.strip() != ""]),
            msg=msg
        )

    def check_content(self, objs: List, products: List[str], msg=None):
        for obj in objs:
            file_obj = obj.Object()
            test_bucket = self.mock_s3.Bucket(file_obj.bucket_name)
            if not file_obj.key.endswith(PROD_INFO_SUFFIX):
                if not is_metadata(file_obj.key):
                    self.check_product(file_obj.key, products, test_bucket, msg)
                else:
                    self.assertNotIn(PRODUCT_META_KEY, file_obj.metadata, msg=msg)
                    if file_obj.key.endswith("maven-metadata.xml"):
                        sha1_checksum = file_obj.metadata[CHECKSUM_META_KEY].strip()
                        sha1_obj = test_bucket.Object(file_obj.key + ".sha1")
                        sha1_file_content = str(sha1_obj.get()['Body'].read(), 'utf-8')
                        self.assertEqual(sha1_checksum, sha1_file_content, msg=msg)
                self.assertIn(CHECKSUM_META_KEY, file_obj.metadata, msg=msg)
                self.assertNotEqual("", file_obj.metadata[CHECKSUM_META_KEY].strip(), msg=msg)
