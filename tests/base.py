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
import tempfile
import os
import shutil
from charon.utils.files import overwrite_file
from charon.config import CONFIG_FILE

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

targets:
    ga:
        bucket: "charon-test"
        prefix: ga
    ea:
        bucket: "charon-test-ea"
        prefix: earlyaccess/all
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
        shutil.copytree(os.path.join(os.getcwd(), "template"), template_path)
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
