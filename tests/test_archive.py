from tests.base import BaseTest
from charon.utils.archive import NpmArchiveType, detect_npm_archive
import os

from tests.constants import INPUTS


class ArchiveTest(BaseTest):
    def test_detect_package(self):
        mvn_tarball = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        self.assertEqual(NpmArchiveType.NOT_NPM, detect_npm_archive(mvn_tarball))
        npm_tarball = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        self.assertEqual(NpmArchiveType.TAR_FILE, detect_npm_archive(npm_tarball))

    def test_download_archive(self):
        pass
