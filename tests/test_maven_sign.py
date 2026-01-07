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
from charon.pkgs.maven import handle_maven_uploading
from tests.base import PackageBaseTest
from tests.commons import (
    TEST_BUCKET, COMMONS_CLIENT_456_SIGNS, COMMONS_LOGGING_SIGNS, COMMONS_CLIENT_456_INDEX,
    COMMONS_CLIENT_459_SIGNS
)
from moto import mock_aws
import os

from tests.constants import INPUTS


@mock_aws
class MavenFileSignTest(PackageBaseTest):

    def test_uploading_sign(self):
        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            [test_zip], product,
            targets=[('', TEST_BUCKET, '', '')],
            dir_=self.tempdir,
            gen_sign=True,
            key="random"
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]

        self.assertEqual(46, len(actual_files))

        for f in COMMONS_LOGGING_SIGNS:
            self.assertIn(f, actual_files)

        for f in COMMONS_CLIENT_456_SIGNS:
            self.assertIn(f, actual_files)

        indedx_obj = test_bucket.Object(COMMONS_CLIENT_456_INDEX)
        index_content = str(indedx_obj.get()["Body"].read(), "utf-8")
        self.assertIn(
            "<a href=\"httpclient-4.5.6.jar.asc\" "
            "title=\"httpclient-4.5.6.jar.asc\">httpclient-4.5.6.jar.asc</a>",
            index_content
        )

    def test_overlap_upload_index(self):
        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            [test_zip], product_456,
            targets=[('', TEST_BUCKET, '', '')],
            dir_=self.tempdir,
            gen_sign=True,
            key="random"
        )

        test_zip = os.path.join(INPUTS, "commons-client-4.5.9.zip")
        product_459 = "commons-client-4.5.9"
        handle_maven_uploading(
            [test_zip], product_459,
            targets=[('', TEST_BUCKET, '', '')],
            dir_=self.tempdir,
            gen_sign=True,
            key="random"
        )

        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        objs = list(test_bucket.objects.all())
        actual_files = [obj.key for obj in objs]

        self.assertEqual(57, len(objs))

        for f in COMMONS_LOGGING_SIGNS:
            self.assertIn(f, actual_files)

        for f in COMMONS_CLIENT_456_SIGNS:
            self.assertIn(f, actual_files)

        for f in COMMONS_CLIENT_459_SIGNS:
            self.assertIn(f, actual_files)
