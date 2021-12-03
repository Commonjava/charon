"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
import os
import charon.config as config
from tests.base import BaseTest


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.__base = BaseTest()

    def tearDown(self) -> None:
        self.__base.tearDown()

    def test_config(self):
        self.__base.setUp()
        conf = config.get_config()
        self.assertEqual([".*^(redhat).*", ".*snapshot.*"], conf.get_ignore_patterns())
        self.assertEqual('charon-test', conf.get_aws_bucket("ga"))
        self.assertEqual('ga', conf.get_bucket_prefix("ga"))
        self.assertEqual('charon-test-ea', conf.get_aws_bucket("ea"))
        self.assertEqual('earlyaccess/all', conf.get_bucket_prefix("ea"))

    def test_no_config(self):
        self.__base.change_home()
        conf = config.get_config()
        self.assertIsNone(conf)

    def test_config_missing_targets(self):
        content_missing_targets = """
ignore_patterns:
    - ".*^(redhat).*"
    - ".*snapshot.*"
        """
        self.__change_config_content(content_missing_targets)
        conf = config.get_config()
        self.assertIsNone(conf)

    def test_config_missing_bucket(self):
        content_missing_targets = """
ignore_patterns:
    - ".*^(redhat).*"
    - ".*snapshot.*"

targets:
    ga:
        prefix: ga
        """
        self.__change_config_content(content_missing_targets)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        self.assertEqual("ga", conf.get_bucket_prefix("ga"))
        self.assertIsNone(conf.get_aws_bucket("ga"))

    def test_config_missing_prefix(self):
        content_missing_targets = """
ignore_patterns:
    - ".*^(redhat).*"
    - ".*snapshot.*"

targets:
    ga:
        bucket: charon-test
        """
        self.__change_config_content(content_missing_targets)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        self.assertEqual("charon-test", conf.get_aws_bucket("ga"))
        self.assertEqual("", conf.get_bucket_prefix("ga"))

    def __change_config_content(self, content: str):
        self.__base.change_home()
        config_base = self.__base.get_config_base()
        os.mkdir(config_base)
        self.__base.prepare_config(config_base, content)
