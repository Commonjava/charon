import unittest
import tempfile
import os
import shutil


class BaseMRRCTest(unittest.TestCase):
    def setUp(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix="mrrc-test-")
        # Configure environment and copy config files and templates
        os.environ["HOME"] = self.tempdir
        mrrc_config_base = os.path.join(self.tempdir, ".mrrc")
        mrrc_template_path = os.path.join(mrrc_config_base, "template")
        os.mkdir(mrrc_config_base)
        shutil.copytree(os.path.join(os.getcwd(), "template"), mrrc_template_path)
        if not os.path.isdir(mrrc_template_path):
            self.fail("Template initilization failed!")
        shutil.copyfile(
            os.path.join(os.getcwd(), "config/mrrc-uploader.conf"),
            os.path.join(mrrc_config_base, "mrrc-uploader.conf"),
        )
        if not os.path.isfile(os.path.join(mrrc_config_base, "mrrc-uploader.conf")):
            self.fail("Configuration initilization failed!")

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ
