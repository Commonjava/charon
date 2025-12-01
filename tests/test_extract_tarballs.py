from tests.base import BaseTest
from charon.pkgs.maven import _extract_tarballs
import os

from tests.constants import INPUTS


class ArchiveTest(BaseTest):
    def test_extract_tarballs(self):
        mvn_tarballs = [
            os.path.join(INPUTS, "commons-client-4.5.6.zip"),
            os.path.join(INPUTS, "commons-client-4.5.9.zip"),
        ]
        final_merged_path = _extract_tarballs(mvn_tarballs, "maven-repository")
        expected_dir = os.path.join(
            final_merged_path, "merged_repositories", "maven-repository"
        )
        self.assertTrue(os.path.exists(expected_dir))

        expected_files = [
            "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar",
            "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom",
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar",
            "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom",
        ]
        for expected_file in expected_files:
            file_path = os.path.join(expected_dir, expected_file)
            self.assertTrue(os.path.exists(file_path))
