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

import logging
import unittest
import tempfile
import os
import json
import shutil
from unittest import mock
from charon.utils.files import overwrite_file
from charon.pkgs.radas_sign import generate_radas_sign

logger = logging.getLogger(__name__)


class RadasSignHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.__prepare_sign_result_file()

    def tearDown(self) -> None:
        super().tearDown()
        self.__clear_sign_result_file()

    def test_multi_sign_files_generation(self):
        self.__prepare_artifacts()
        failed, generated = generate_radas_sign(
            self.__repo_dir, self.__root, self.__sign_result_file
        )
        self.assertEqual(failed, [])
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")
        expected_asc3 = os.path.join(self.__repo_dir, "foo/bar/3.0/foo-bar-3.0.jar.asc")
        expected_asc4 = os.path.join(self.__repo_dir, "foo/bar/4.0/foo-bar-4.0.jar.asc")
        self.assertEqual(len(generated), 4)
        self.assertIn(expected_asc1, generated)
        self.assertIn(expected_asc2, generated)
        self.assertIn(expected_asc3, generated)
        self.assertIn(expected_asc4, generated)

        with open(expected_asc1) as f:
            content1 = f.read()
        with open(expected_asc2) as f:
            content2 = f.read()
        self.assertIn("signature1@hash", content1)
        self.assertIn("signature2@hash", content2)

    def test_sign_files_generation_with_missing_artifacts(self):
        failed, generated = generate_radas_sign(
            self.__repo_dir, self.__root, self.__sign_result_file
        )
        self.assertEqual(failed, [])
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")
        self.assertEqual(generated, [])
        self.assertFalse(os.path.exists(expected_asc1))
        self.assertFalse(os.path.exists(expected_asc2))

    def test_sign_files_generation_with_failure(self):
        self.__prepare_artifacts()
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")

        # simulate expected_asc1 can not be written properly
        real_overwrite = overwrite_file
        with mock.patch("charon.pkgs.radas_sign.files.overwrite_file") as mock_overwrite:

            def side_effect(path, content):
                if path == expected_asc1:
                    raise IOError("mock write error")
                return real_overwrite(path, content)

            mock_overwrite.side_effect = side_effect
            failed, generated = generate_radas_sign(
                self.__repo_dir, self.__root, self.__sign_result_file
            )

        self.assertEqual(len(failed), 1)
        self.assertNotIn(expected_asc1, generated)
        self.assertIn(expected_asc2, generated)

    def test_sign_files_generation_with_missing_result(self):
        self.__prepare_artifacts()
        # simulate missing pull result by removing the sign result file loc
        shutil.rmtree(self.__sign_result_loc)

        failed, generated = generate_radas_sign(
            self.__repo_dir, self.__root, self.__sign_result_file
        )
        self.assertEqual(failed, [])
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")
        self.assertEqual(generated, [])
        self.assertFalse(os.path.exists(expected_asc1))
        self.assertFalse(os.path.exists(expected_asc2))

    def __prepare_sign_result_file(self):
        self.__sign_result_loc = tempfile.mkdtemp()
        self.__sign_result_file = os.path.join(self.__sign_result_loc, "result.json")
        self.__root = "maven-repository"
        self.__repo_dir = os.path.join(tempfile.mkdtemp(), "maven-repository")
        data = {
            "request-id": "request-id",
            "file-reference": "quay.io/org/maven-zip@hash",
            "results": [
                {
                    "file": "maven-repository/foo/bar/1.0/foo-bar-1.0.jar",
                    "signature": (
                        "-----BEGIN PGP SIGNATURE-----"
                        "signature1@hash"
                        "-----END PGP SIGNATURE-----"
                    ),
                    "checksum": "sha256:sha256-content",
                },
                {
                    "file": "maven-repository/foo/bar/2.0/foo-bar-2.0.jar",
                    "signature": (
                        "-----BEGIN PGP SIGNATURE-----"
                        "signature2@hash"
                        "-----END PGP SIGNATURE-----"
                    ),
                    "checksum": "sha256:sha256-content",
                },
                {
                    "file": "README.md",
                    "signature": (
                        "-----BEGIN PGP SIGNATURE-----"
                        "signature2@hash"
                        "-----END PGP SIGNATURE-----"
                    ),
                    "checksum": "sha256:sha256-content",
                },
                {
                    "file": "radas-tmp/maven-repository/foo/bar/3.0/foo-bar-3.0.jar",
                    "signature": (
                        "-----BEGIN PGP SIGNATURE-----"
                        "signature2@hash"
                        "-----END PGP SIGNATURE-----"
                    ),
                    "checksum": "sha256:sha256-content",
                },
                {
                    "file": "foo/bar/4.0/foo-bar-4.0.jar",
                    "signature": (
                        "-----BEGIN PGP SIGNATURE-----"
                        "signature2@hash"
                        "-----END PGP SIGNATURE-----"
                    ),
                    "checksum": "sha256:sha256-content",
                },
            ],
        }
        json_str = json.dumps(data, indent=2)
        overwrite_file(self.__sign_result_file, json_str)

    def __prepare_artifacts(self):
        for version in ["1.0", "2.0", "3.0", "4.0"]:
            dir_path = os.path.join(self.__repo_dir, f"foo/bar/{version}")
            os.makedirs(dir_path, exist_ok=True)

            artifact_path = os.path.join(dir_path, f"foo-bar-{version}.jar")
            with open(artifact_path, "w") as f:
                f.write("dummy")

    def __clear_sign_result_file(self):
        if os.path.exists(self.__sign_result_loc):
            shutil.rmtree(self.__sign_result_loc)
        if os.path.exists(self.__repo_dir):
            shutil.rmtree(self.__repo_dir)
