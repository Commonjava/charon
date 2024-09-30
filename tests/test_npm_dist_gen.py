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
import os
import subresource_integrity
from moto import mock_aws
from charon.pkgs.npm import handle_npm_uploading
from charon.utils.files import digest, HashType
from tests.base import PackageBaseTest
from tests.commons import (
    TEST_BUCKET, TEST_BUCKET_2,
    CODE_FRAME_META, CODE_FRAME_7_14_5_META
)
from tests.constants import INPUTS


@mock_aws
class NPMUploadTest(PackageBaseTest):
    def setUp(self):
        super().setUp()
        self.mock_s3.create_bucket(Bucket=TEST_BUCKET_2)
        self.test_bucket_2 = self.mock_s3.Bucket(TEST_BUCKET_2)

    def test_dist_gen_in_single_target(self):
        targets_ = [('', TEST_BUCKET, '', "npm1.registry.redhat.com")]
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=targets_,
            dir_=self.tempdir, do_index=False
        )
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        meta_obj_client_7_14_5 = test_bucket.Object(CODE_FRAME_7_14_5_META)
        meta_content_client_7_14_5 = str(meta_obj_client_7_14_5.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", meta_content_client_7_14_5)
        self.assertIn("\"tarball\": \"https://npm1.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", meta_content_client_7_14_5)
        self.assertIn("\"shasum\": \"23b08d740e83f49c5e59945fbf1b43e80bbf4edb\"",
                      meta_content_client_7_14_5)
        self.assertIn("\"integrity\": "
                      "\"sha512-9pzDqyc6OLDaqe+zbACgFkb6fKMNG6CObKpnYXChRsvYGyEdc7CA2BaqeOM"
                      "+vOtCS5ndmJicPJhKAwYRI6UfFw==\"",
                      meta_content_client_7_14_5)

        sha1 = digest(test_tgz, HashType.SHA1)
        self.assertEqual(sha1, "23b08d740e83f49c5e59945fbf1b43e80bbf4edb")
        with open(test_tgz, "rb") as tarball:
            tarball_data = tarball.read()
            sha512 = subresource_integrity.render(tarball_data, ['sha512'])
            self.assertEqual(sha512,
                             "sha512-9pzDqyc6OLDaqe+zbACgFkb6fKMNG6CObKpnYXChRsvYGyEdc7CA2BaqeOM"
                             "+vOtCS5ndmJicPJhKAwYRI6UfFw==")

        merged_meta_obj_client = test_bucket.Object(CODE_FRAME_META)
        merged_meta_content_client = str(merged_meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", merged_meta_content_client)
        self.assertIn("\"tarball\": \"https://npm1.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", merged_meta_content_client)
        self.assertIn("\"shasum\": \"23b08d740e83f49c5e59945fbf1b43e80bbf4edb\"",
                      merged_meta_content_client)
        self.assertIn("\"integrity\": "
                      "\"sha512-9pzDqyc6OLDaqe+zbACgFkb6fKMNG6CObKpnYXChRsvYGyEdc7CA2BaqeOM"
                      "+vOtCS5ndmJicPJhKAwYRI6UfFw==\"", merged_meta_content_client)

    def test_dist_gen_in_multi_targets(self):
        targets_ = [('', TEST_BUCKET, '', "npm1.registry.redhat.com"),
                    ('', TEST_BUCKET_2, '', "npm2.registry.redhat.com")]
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=targets_,
            dir_=self.tempdir, do_index=False
        )
        test_bucket_1 = self.mock_s3.Bucket(TEST_BUCKET)
        meta_obj_client_7_14_5 = test_bucket_1.Object(CODE_FRAME_7_14_5_META)
        meta_content_client_7_14_5 = str(meta_obj_client_7_14_5.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", meta_content_client_7_14_5)
        self.assertIn("\"tarball\": \"https://npm1.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", meta_content_client_7_14_5)

        merged_meta_obj_client_1 = test_bucket_1.Object(CODE_FRAME_META)
        merged_meta_content_client = str(merged_meta_obj_client_1.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", merged_meta_content_client)
        self.assertIn("\"tarball\": \"https://npm1.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", merged_meta_content_client)

        test_bucket_2 = self.mock_s3.Bucket(TEST_BUCKET_2)
        meta_obj_client_7_14_5 = test_bucket_2.Object(CODE_FRAME_7_14_5_META)
        meta_content_client_7_14_5 = str(meta_obj_client_7_14_5.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", meta_content_client_7_14_5)
        self.assertIn("\"tarball\": \"https://npm2.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", meta_content_client_7_14_5)

        merged_meta_obj_client_2 = test_bucket_2.Object(CODE_FRAME_META)
        merged_meta_content_client = str(merged_meta_obj_client_2.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", merged_meta_content_client)
        self.assertIn("\"tarball\": \"https://npm2.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", merged_meta_content_client)

    def test_overlapping_registry_dist_gen(self):
        targets_ = [('', TEST_BUCKET, '', "npm1.registry.redhat.com")]
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=targets_,
            dir_=self.tempdir, do_index=False
        )
        test_bucket = self.mock_s3.Bucket(TEST_BUCKET)
        meta_obj_client_7_14_5 = test_bucket.Object(CODE_FRAME_7_14_5_META)
        meta_content_client_7_14_5 = str(meta_obj_client_7_14_5.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", meta_content_client_7_14_5)
        self.assertIn("\"tarball\": \"https://npm1.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", meta_content_client_7_14_5)

        merged_meta_obj_client = test_bucket.Object(CODE_FRAME_META)
        merged_meta_content_client = str(merged_meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", merged_meta_content_client)
        self.assertIn("\"tarball\": \"https://npm1.registry.redhat.com/@babel/code-frame/-/code"
                      "-frame-7.14.5.tgz\"", merged_meta_content_client)

        targets_overlapping_ = [('', TEST_BUCKET, '', "npm1.overlapping.registry.redhat.com")]
        test_tgz = os.path.join(INPUTS, "code-frame-7.14.5.tgz")
        product_7_14_5 = "code-frame-7.14.5"
        handle_npm_uploading(
            test_tgz, product_7_14_5,
            targets=targets_overlapping_,
            dir_=self.tempdir, do_index=False
        )

        meta_obj_client_7_14_5 = test_bucket.Object(CODE_FRAME_7_14_5_META)
        meta_content_client_7_14_5 = str(meta_obj_client_7_14_5.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", meta_content_client_7_14_5)
        self.assertIn("\"tarball\": \"https://npm1.overlapping.registry.redhat.com/@babel/code"
                      "-frame/-/code-frame-7.14.5.tgz\"", meta_content_client_7_14_5)

        merged_meta_obj_client = test_bucket.Object(CODE_FRAME_META)
        merged_meta_content_client = str(merged_meta_obj_client.get()["Body"].read(), "utf-8")
        self.assertIn("\"dist\"", merged_meta_content_client)
        self.assertIn("\"tarball\": \"https://npm1.overlapping.registry.redhat.com/@babel/code"
                      "-frame/-/code-frame-7.14.5.tgz\"", merged_meta_content_client)
