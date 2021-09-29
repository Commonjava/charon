"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

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
import mrrc.config as config
from tests.base import BaseMRRCTest


class ConfigTest(BaseMRRCTest):
    def test_config(self):
        conf = config.mrrc_config()
        self.assertEqual([".*^(redhat).*", ".*snapshot.*"], conf.get_ignore_patterns())
        self.assertEqual('FakeKey', conf.get_aws_key_id())
        self.assertEqual('FakePassword', conf.get_aws_key())
        aws_configs = conf.get_aws_configs()
        # self.assertEqual('https://s3.fake.com', aws_configs['endpoint_url'])
        self.assertEqual('us-east-1', aws_configs['region'])
        self.assertEqual('10', aws_configs['retry_max_attempts'])
        self.assertEqual('standard', aws_configs['retry_mode'])
