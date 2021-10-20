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
import tempfile
import os
import shutil
from mrrc.utils.files import write_file


class BaseMRRCTest(unittest.TestCase):
    def setUp(self):
        self.change_home()
        mrrc_config_base = os.path.join(self.tempdir, '.mrrc')
        self.__prepare_template(mrrc_config_base)
        default_config_content = """
        [mrrc]
        ignore_patterns = [".*^(redhat).*",".*snapshot.*"]
        bucket = mrrc-test
        """
        self.prepare_config(mrrc_config_base, default_config_content)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ

    def change_home(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='mrrc-test-')
        # Configure environment and copy templates
        os.environ['HOME'] = self.tempdir

    def __prepare_template(self, config_base):
        mrrc_template_path = os.path.join(config_base, 'template')
        os.mkdir(config_base)
        shutil.copytree(os.path.join(os.getcwd(), "template"), mrrc_template_path)
        if not os.path.isdir(mrrc_template_path):
            self.fail("Template initilization failed!")

    def prepare_config(self, config_base, file_content):
        config_path = os.path.join(config_base, "mrrc-uploader.conf")
        write_file(config_path, file_content)
        if not os.path.isfile(config_path):
            self.fail("Configuration initilization failed!")

    def get_temp_dir(self) -> str:
        return self.tempdir
