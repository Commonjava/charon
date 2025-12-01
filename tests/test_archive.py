from tests.base import BaseTest
from charon.utils.archive import NpmArchiveType, detect_npm_archive, detect_npm_archives
import os

from tests.constants import INPUTS


class ArchiveTest(BaseTest):
    def test_detect_package(self):
        mvn_tarball = os.path.join(INPUTS, "commons-client-4.5.6.zip")
        self.assertEqual(NpmArchiveType.NOT_NPM, detect_npm_archive(mvn_tarball))
        npm_tarball = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        self.assertEqual(NpmArchiveType.TAR_FILE, detect_npm_archive(npm_tarball))

    def test_detect_packages(self):
        mvn_tarballs = [
            os.path.join(INPUTS, "commons-client-4.5.6.zip"),
            os.path.join(INPUTS, "commons-client-4.5.9.zip")
        ]
        archive_types = detect_npm_archives(mvn_tarballs)
        self.assertEqual(2, archive_types.count(NpmArchiveType.NOT_NPM))

        npm_tarball = [
            os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        ]
        archive_types = detect_npm_archives(npm_tarball)
        self.assertEqual(1, archive_types.count(NpmArchiveType.TAR_FILE))

        npm_tarballs = [
            os.path.join(INPUTS, "code-frame-7.14.5.tgz"),
            os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        ]
        archive_types = detect_npm_archives(npm_tarballs)
        self.assertEqual(2, archive_types.count(NpmArchiveType.TAR_FILE))

        tarballs = [
            os.path.join(INPUTS, "commons-client-4.5.6.zip"),
            os.path.join(INPUTS, "commons-client-4.5.9.zip"),
            os.path.join(INPUTS, "code-frame-7.14.5.tgz"),
            os.path.join(INPUTS, "code-frame-7.15.8.tgz")
        ]
        archive_types = detect_npm_archives(tarballs)
        self.assertEqual(2, archive_types.count(NpmArchiveType.NOT_NPM))
        self.assertEqual(2, archive_types.count(NpmArchiveType.TAR_FILE))

    def test_download_archive(self):
        pass
