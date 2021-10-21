from tests.base import BaseMRRCTest
from mrrc.utils.archive import NpmArchiveType, detect_npm_archive
import os


class ArchiveTest(BaseMRRCTest):
    def test_detect_package(self):
        mvn_tarball = os.path.join(os.getcwd(), "tests/input/commons-client-4.5.6.zip")
        self.assertEqual(NpmArchiveType.NOT_NPM, detect_npm_archive(mvn_tarball))
        npm_tarball = os.path.join(os.getcwd(), "tests/input/code-frame-7.14.5.tgz")
        self.assertEqual(NpmArchiveType.TAR_FILE, detect_npm_archive(npm_tarball))

    def test_download_archive(self):
        pass
