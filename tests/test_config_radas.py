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
import os
import charon.config as config
import shutil
import tempfile
from tests.base import BaseTest
from charon.utils.files import overwrite_file


class RadasConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.__base = BaseTest()
        self.__prepare_ca()

    def tearDown(self) -> None:
        self.__base.tearDown()
        self.__clear_ca()

    def test_full_radas_config(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    result_queue: queue.result.test
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}
    root_ca: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path,
                   self.__client_key_pass_file, self.__root_ca)
        print(radas_settings)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertTrue(rconf.validate())

    def test_missing_umb_host(self):
        radas_settings = """
radas:
    result_queue: queue.result.test
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path, self.__client_key_pass_file)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def test_missing_result_queue(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path, self.__client_key_pass_file)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def test_missing_request_queue(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    result_queue: queue.result.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path, self.__client_key_pass_file)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def test_unaccessible_client_ca(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    result_queue: queue.result.test
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path, self.__client_key_pass_file)
        os.remove(self.__client_ca_path)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def test_unaccessible_client_key(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    result_queue: queue.result.test
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path, self.__client_key_pass_file)
        os.remove(self.__client_key_path)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def test_unaccessible_client_password_file(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    result_queue: queue.result.test
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path, self.__client_key_pass_file)
        os.remove(self.__client_key_pass_file)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def test_unaccessible_root_ca(self):
        radas_settings = """
radas:
    umb_host: test.umb.api.com
    result_queue: queue.result.test
    request_queue: queue.request.test
    client_ca: {}
    client_key: {}
    client_key_pass_file: {}
    root_ca: {}

targets:
    ga:
    - bucket: charon-test
        """.format(self.__client_ca_path, self.__client_key_path,
                   self.__client_key_pass_file, self.__root_ca)
        os.remove(self.__root_ca)
        self.__change_config_content(radas_settings)
        conf = config.get_config()
        self.assertIsNotNone(conf)
        rconf = conf.get_radas_config()
        self.assertIsNotNone(rconf)
        self.assertFalse(rconf.validate())

    def __change_config_content(self, content: str):
        self.__base.change_home()
        config_base = self.__base.get_config_base()
        os.mkdir(config_base)
        self.__base.prepare_config(config_base, content)

    def __prepare_ca(self):
        self.__tempdir = tempfile.mkdtemp()
        self.__client_ca_path = os.path.join(self.__tempdir, "client_ca.crt")
        self.__client_key_path = os.path.join(self.__tempdir, "client_key.crt")
        self.__client_key_pass_file = os.path.join(self.__tempdir, "client_key_password.txt")
        self.__root_ca = os.path.join(self.__tempdir, "root_ca.crt")
        overwrite_file(self.__client_ca_path, "client ca")
        overwrite_file(self.__client_key_path, "client key")
        overwrite_file(self.__client_key_pass_file, "it's password")
        overwrite_file(self.__root_ca, "root ca")

    def __clear_ca(self):
        shutil.rmtree(self.__tempdir)
