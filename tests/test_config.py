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
import unittest
import os
import mrrc.config as config
from tests.base import BaseMRRCTest


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.__base = BaseMRRCTest()

    def tearDown(self) -> None:
        self.__base.tearDown()

    def test_config(self):
        self.__base.setUp()
        conf = config.mrrc_config()
        self.assertEqual([".*^(redhat).*", ".*snapshot.*"], conf.get_ignore_patterns())
        self.assertEqual('mrrc-test', conf.get_aws_bucket())

    def test_no_config(self):
        self.__base.change_home()
        conf = config.mrrc_config()
        self.assertIsNone(conf)

    def test_config_default(self):
        self.__base.change_home()
        default_config_content = """
        [mrrc]
        """
        mrrc_config_base = os.path.join(self.__base.get_temp_dir(), '.mrrc')
        os.mkdir(mrrc_config_base)
        self.__base.prepare_config(mrrc_config_base, default_config_content)

        conf = config.mrrc_config()
        self.assertEqual(None, conf.get_ignore_patterns())
        self.assertEqual('mrrc', conf.get_aws_bucket())
