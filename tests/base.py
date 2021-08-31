import mrrc.metadata_mvn as mvn
import unittest
import tempfile
import os
import shutil

class BaseMRRCTest(unittest.TestCase):
    def setUp(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='mrrc-')
        # Configure environment and copy config files and templates
        os.environ['HOME'] = self.tempdir
        mrrc_config_base = os.path.join(self.tempdir, '.mrrc' )
        mrrc_template_path = os.path.join(mrrc_config_base, 'template' )
        os.mkdir(mrrc_config_base)
        shutil.copytree(os.path.join(os.getcwd(),"template"), mrrc_template_path)
        shutil.copyfile(os.path.join(os.getcwd(), "config/mrrc-uploader.conf"), os.path.join(mrrc_config_base, "mrrc-uploader.conf"))

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ
