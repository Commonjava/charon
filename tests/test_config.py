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
from typing import List
import unittest
import os
import charon.config as config
import re
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
        self.assertEqual('npm1.registry.redhat.com', conf.get_bucket_registry("npm"))

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

    def test_config_missing_registry(self):
        content_missing_registry = """
ignore_patterns:
    - ".*^(redhat).*"
    - ".*snapshot.*"

targets:
    npm:
        bucket: charon-npm-test
        """
        self.__change_config_content(content_missing_registry)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        self.assertEqual("charon-npm-test", conf.get_aws_bucket("npm"))
        self.assertEqual("localhost", conf.get_bucket_registry("npm"))

    def test_ignore_patterns(self):
        # pylint: disable=anomalous-backslash-in-string
        content_missing_targets = """
ignore_patterns:
    - '\.nexus.*' # noqa: W605
    - '\.index.*' # noqa: W605
    - '\.meta.*' # noqa: W605
    - '\..+'  # path with a filename that starts with a dot # noqa: W605
    - 'index\.html.*' # noqa: W605

targets:
    ga:
        bucket: charon-test
        """
        self.__change_config_content(content_missing_targets)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        self.assertEqual(5, len(conf.get_ignore_patterns()))
        self.assertTrue(self.__is_ignored(".index.html", conf.get_ignore_patterns()))
        self.assertTrue(self.__is_ignored(".abcxyz.jar", conf.get_ignore_patterns()))
        self.assertTrue(self.__is_ignored("index.html", conf.get_ignore_patterns()))
        self.assertTrue(self.__is_ignored(".nexuxabc", conf.get_ignore_patterns()))
        self.assertFalse(self.__is_ignored("abcxyz.jar", conf.get_ignore_patterns()))
        self.assertFalse(self.__is_ignored("abcxyz.pom", conf.get_ignore_patterns()))
        self.assertFalse(self.__is_ignored("abcxyz.jar.md5", conf.get_ignore_patterns()))

    def __change_config_content(self, content: str):
        self.__base.change_home()
        config_base = self.__base.get_config_base()
        os.mkdir(config_base)
        self.__base.prepare_config(config_base, content)

    def __is_ignored(self, filename: str, ignore_patterns:  List[str]) -> bool:
        if ignore_patterns:
            for dirs in ignore_patterns:
                if re.match(dirs, filename):
                    return True
        return False
