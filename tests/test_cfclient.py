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
from tests.base import BaseTest
from tests.constants import TEST_DS_CONFIG
from charon.cache import CFClient
from moto import mock_aws
import boto3


@mock_aws
class CFClientTest(BaseTest):
    def setUp(self):
        super().setUp()
        # mock_cf is used to generate expected content
        self.mock_cf = self.__prepare_cf()
        response = self.mock_cf.create_distribution(DistributionConfig=TEST_DS_CONFIG)
        self.test_dist_id = response.get('Distribution').get('Id')
        # cf_client is the client we will test
        self.cf_client = CFClient()

    def tearDown(self):
        self.mock_cf.delete_distribution(Id=self.test_dist_id, IfMatch=".")
        super().tearDown()

    def __prepare_cf(self):
        return boto3.client('cloudfront')

    def test_get_distribution_id(self):
        dist_id = self.cf_client.get_dist_id_by_domain("maven.repository.redhat.com")
        self.assertIsNotNone(dist_id)
        dist_id = self.cf_client.get_dist_id_by_domain("notexists.redhat.com")
        self.assertIsNone(dist_id)

    def test_invalidate_paths_single(self):
        dist_id = self.cf_client.get_dist_id_by_domain("maven.repository.redhat.com")
        result = self.cf_client.invalidate_paths(dist_id, ["/*"])
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['Id'])
        self.assertEqual('completed', str.lower(result[0]['Status']))
        status = self.cf_client.invalidate_paths("noexists_id", ["/*"])
        self.assertFalse(status)

    def test_invalidate_paths_multi(self):
        dist_id = self.cf_client.get_dist_id_by_domain("maven.repository.redhat.com")
        result = self.cf_client.invalidate_paths(dist_id, ["/1", "/2", "/3"], batch_size=1)
        self.assertEqual(len(result), 3)
        for r in result:
            self.assertTrue(r['Id'])
            self.assertEqual('completed', str.lower(r['Status']))

    def test_check_invalidation(self):
        dist_id = self.cf_client.get_dist_id_by_domain("maven.repository.redhat.com")
        result = self.cf_client.invalidate_paths(dist_id, ["/*"])
        invalidation = self.cf_client.check_invalidation(dist_id, result[0]['Id'])
        self.assertIsNotNone(invalidation['Id'])
        self.assertEqual('completed', str.lower(result[0]['Status']))
