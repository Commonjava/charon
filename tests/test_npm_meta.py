import os
import json
import shutil
import marshmallow_dataclass
import mrrc.utils.archive as archive
from mrrc.pkgs.npm import NPMPackageMetadata, scan_for_version, gen_package_metadata_file
from tests.base import BaseMRRCTest


class NPMMetadataTest(BaseMRRCTest):

    def test_scan_for_version(self):
        version_json_file_path = os.path.join(os.getcwd(), 'tests-input/code-frame_7.14.5.json')
        version = scan_for_version(version_json_file_path)
        self.assertEqual('@babel/code-frame', version.get_name())
        self.assertEqual('7.14.5', version.get_version())
        self.assertEqual('MIT', version.get_license())
        self.assertEqual('https://registry.npmjs.org/@babel/code-frame/-/code-frame-7.14.5.tgz', version.get_dist()['tarball'])
        self.assertEqual(4, version.get_dist()['fileCount'])

    def test_gen_package_meta_file(self):
        temp_root = os.path.join(self.tempdir, 'tmp_tgz')
        os.mkdir(temp_root)
        tarball_test_path = os.path.join(os.getcwd(), 'tests-input/kogito-tooling-workspace-0.9.0-3.tgz')
        version_path = archive.extract_npm_tarball(tarball_test_path, temp_root)
        version = scan_for_version(version_path)
        gen_package_metadata_file(version, temp_root)

        npm_meta_file = os.path.join(temp_root, '@redhat/kogito-tooling-workspace/package.json')
        if not os.path.isfile(npm_meta_file):
            self.fail('package.json is not generated correctly!')
        with open(npm_meta_file) as verified_package_meta_file:
            verified_package_meta_data = json.load(verified_package_meta_file)
        package_schema = marshmallow_dataclass.class_schema(NPMPackageMetadata)()
        verified_package = package_schema.load(verified_package_meta_data)
        name = verified_package.name
        self.assertEqual('@redhat/kogito-tooling-workspace', name)
        license = verified_package.license
        self.assertEqual('Apache-2.0', license)
        repo = verified_package.repository
        self.assertEqual('git', repo['type'])
        self.assertEqual('https://github.com/kiegroup/kogito-tooling.git', repo['url'])

        shutil.rmtree(temp_root)