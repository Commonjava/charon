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

class BaseMRRCTest(unittest.TestCase):
    def setUp(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='mrrc-test-')
        # Configure environment and copy config files and templates
        os.environ['HOME'] = self.tempdir
        mrrc_config_base = os.path.join(self.tempdir, '.mrrc' )
        mrrc_template_path = os.path.join(mrrc_config_base, 'template' )
        os.mkdir(mrrc_config_base)
        shutil.copytree(os.path.join(os.getcwd(),"template"), mrrc_template_path)
        if not os.path.isdir(mrrc_template_path):
            self.fail("Template initilization failed!")
        shutil.copyfile(os.path.join(os.getcwd(), "config/mrrc-uploader.conf"), os.path.join(mrrc_config_base, "mrrc-uploader.conf"))
        if not os.path.isfile(os.path.join(mrrc_config_base, "mrrc-uploader.conf")):
            self.fail("Configuration initilization failed!")

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ
