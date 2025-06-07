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
import builtins
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
        failed, generated = generate_radas_sign(self.__repo_dir, self.__sign_result_loc)
        self.assertEqual(failed, [])
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")
        self.assertEqual(len(generated), 2)
        self.assertIn(expected_asc1, generated)
        self.assertIn(expected_asc2, generated)

        with open(expected_asc1) as f:
            content1 = f.read()
        with open(expected_asc2) as f:
            content2 = f.read()
        self.assertIn("signature1@hash", content1)
        self.assertIn("signature2@hash", content2)

    def test_sign_files_generation_with_missing_artifacts(self):
        failed, generated = generate_radas_sign(self.__repo_dir, self.__sign_result_loc)
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

        # simulate expected_asc1 can not open to write properly
        real_open = builtins.open
        with mock.patch("builtins.open") as mock_open:
            def side_effect(path, *args, **kwargs):
                # this is for pylint check
                mode = "r"
                if len(args) > 0:
                    mode = args[0]
                elif "mode" in kwargs:
                    mode = kwargs["mode"]
                if path == expected_asc1 and "w" in mode:
                    raise IOError("mock write error")
                return real_open(path, *args, **kwargs)
            mock_open.side_effect = side_effect
            failed, generated = generate_radas_sign(self.__repo_dir, self.__sign_result_loc)

        self.assertEqual(len(failed), 1)
        self.assertNotIn(expected_asc1, generated)
        self.assertIn(expected_asc2, generated)

    def test_sign_files_generation_with_missing_result(self):
        self.__prepare_artifacts()
        # simulate missing pull result by removing the sign result file loc
        shutil.rmtree(self.__sign_result_loc)

        failed, generated = generate_radas_sign(self.__repo_dir, self.__sign_result_loc)
        self.assertEqual(failed, [])
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")
        self.assertEqual(generated, [])
        self.assertFalse(os.path.exists(expected_asc1))
        self.assertFalse(os.path.exists(expected_asc2))

    def test_sign_files_generation_with_not_single_results(self):
        self.__prepare_artifacts()
        another_result_file = os.path.join(self.__sign_result_loc, "result2.json")
        overwrite_file(another_result_file, "test_json")

        failed, generated = generate_radas_sign(self.__repo_dir, self.__sign_result_loc)
        self.assertEqual(failed, [])
        expected_asc1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar.asc")
        expected_asc2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar.asc")
        self.assertEqual(generated, [])
        self.assertFalse(os.path.exists(expected_asc1))
        self.assertFalse(os.path.exists(expected_asc2))

    def __prepare_sign_result_file(self):
        self.__sign_result_loc = tempfile.mkdtemp()
        self.__sign_result_file = os.path.join(self.__sign_result_loc, "result.json")
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
            ],
        }
        json_str = json.dumps(data, indent=2)
        overwrite_file(self.__sign_result_file, json_str)

    def __prepare_artifacts(self):
        os.makedirs(os.path.join(self.__repo_dir, "foo/bar/1.0"), exist_ok=True)
        os.makedirs(os.path.join(self.__repo_dir, "foo/bar/2.0"), exist_ok=True)
        artifact1 = os.path.join(self.__repo_dir, "foo/bar/1.0/foo-bar-1.0.jar")
        artifact2 = os.path.join(self.__repo_dir, "foo/bar/2.0/foo-bar-2.0.jar")
        with open(artifact1, "w") as f:
            f.write("dummy1")
        with open(artifact2, "w") as f:
            f.write("dummy2")

    def __clear_sign_result_file(self):
        if os.path.exists(self.__sign_result_loc):
            shutil.rmtree(self.__sign_result_loc)
        if os.path.exists(self.__repo_dir):
            shutil.rmtree(self.__repo_dir)
