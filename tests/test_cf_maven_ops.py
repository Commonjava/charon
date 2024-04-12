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
from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from tests.base import CFBasedTest
from tests.commons import TEST_BUCKET
from tests.constants import INPUTS
from moto import mock_aws
import os


@mock_aws
class CFInMavenOPSTest(CFBasedTest):
    def test_cf_after_upload(self):
        response = self.mock_cf.list_invalidations(DistributionId=self.test_dist_id)
        self.assertIsNotNone(response)
        self.assertEqual(0, response.get('InvalidationList').get('Quantity'))

        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product,
            buckets=[('', TEST_BUCKET, 'ga', '', 'maven.repository.redhat.com')],
            dir_=self.tempdir,
            do_index=True,
            cf_enable=True
        )

        response = self.mock_cf.list_invalidations(DistributionId=self.test_dist_id)
        self.assertEqual(1, response.get('InvalidationList').get('Quantity'))
        items = response.get('InvalidationList').get('Items')
        self.assertEqual(1, len(items))
        self.assertEqual('completed', str.lower(items[0].get('Status')))

    def test_cf_after_del(self):
        response = self.mock_cf.list_invalidations(DistributionId=self.test_dist_id)
        self.assertIsNotNone(response)
        self.assertEqual(0, response.get('InvalidationList').get('Quantity'))

        test_zip = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        product_456 = "commons-client-4.5.6"
        handle_maven_uploading(
            test_zip, product_456,
            buckets=[('', TEST_BUCKET, 'ga', '', 'maven.repository.redhat.com')],
            dir_=self.tempdir,
            do_index=True
        )

        product_456 = "commons-client-4.5.6"
        handle_maven_del(
            test_zip, product_456,
            buckets=[('', TEST_BUCKET, 'ga', '', 'maven.repository.redhat.com')],
            dir_=self.tempdir, do_index=True,
            cf_enable=True
        )

        response = self.mock_cf.list_invalidations(DistributionId=self.test_dist_id)
        self.assertEqual(1, response.get('InvalidationList').get('Quantity'))
        items = response.get('InvalidationList').get('Items')
        self.assertEqual(1, len(items))
        self.assertEqual('completed', str.lower(items[0].get('Status')))
