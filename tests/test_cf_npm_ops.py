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
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from charon.constants import DEFAULT_REGISTRY
from tests.base import CFBasedTest
from tests.commons import TEST_BUCKET
from tests.constants import INPUTS
from moto import mock_aws
import os


@mock_aws
class CFInNPMOPSTest(CFBasedTest):
    def test_cf_after_upload(self):
        response = self.mock_cf.list_invalidations(DistributionId=self.test_dist_id)
        self.assertIsNotNone(response)
        self.assertEqual(0, response.get('InvalidationList').get('Quantity'))

        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, "/", DEFAULT_REGISTRY, "npm.registry.redhat.com")],
            dir_=self.tempdir, do_index=True,
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

        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, '/', DEFAULT_REGISTRY, 'npm.registry.redhat.com')],
            dir_=self.tempdir, do_index=True
        )

        handle_npm_del(
            test_tgz, product_7_14_5,
            targets=[('', TEST_BUCKET, '/', DEFAULT_REGISTRY, 'npm.registry.redhat.com')],
            dir_=self.tempdir, do_index=True,
            cf_enable=True
        )

        response = self.mock_cf.list_invalidations(DistributionId=self.test_dist_id)
        self.assertEqual(1, response.get('InvalidationList').get('Quantity'))
        items = response.get('InvalidationList').get('Items')
        self.assertEqual(1, len(items))
        self.assertEqual('completed', str.lower(items[0].get('Status')))
