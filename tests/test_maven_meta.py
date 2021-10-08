"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

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
import shutil
import zipfile
from xml.dom import minidom

import mrrc.pkgs.maven as mvn
import mrrc.utils.archive as archive
from tests.base import BaseMRRCTest


class MavenMetadataTest(BaseMRRCTest):
    def test_parse_ga(self):
        g, a = mvn.parse_ga("org/apache/maven/plugins/maven-plugin-plugin", "")
        self.assertEqual("org.apache.maven.plugins", g)
        self.assertEqual("maven-plugin-plugin", a)
        g, a = mvn.parse_ga(
            "/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin",
            "/tmp/maven-repository",
        )
        self.assertEqual("org.apache.maven.plugins", g)
        self.assertEqual("maven-plugin-plugin", a)

    def test_parse_gavs(self):
        pom_paths = [
            "/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0.0/"
            "maven-plugin-plugin-1.0.0.pom",
            "/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0.1/"
            "maven-plugin-plugin-1.0.1.pom",
            "/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.2.0/"
            "maven-plugin-plugin-1.2.0.pom",
        ]
        parsed_gavs = mvn.parse_gavs(pom_paths, "/tmp/maven-repository")
        self.assertEqual(
            ["1.0.0", "1.0.1", "1.2.0"],
            parsed_gavs["org.apache.maven.plugins"]["maven-plugin-plugin"],
        )

    def test_gen_meta_file(self):
        test_zip = zipfile.ZipFile(
            os.path.join(os.getcwd(), "tests-input/commons-lang3.zip")
        )
        temp_root = os.path.join(self.tempdir, "tmp_zip")
        os.mkdir(temp_root)
        archive.extract_zip_all(test_zip, temp_root)
        root = os.path.join(
            temp_root, "apache-commons-maven-repository/maven-repository"
        )
        poms = mvn.scan_for_poms(root)
        gav_dict = mvn.parse_gavs(poms, root)
        for g, avs in gav_dict.items():
            for a, vers in avs.items():
                mvn.gen_meta_file(g, a, vers, root)
        maven_meta_file = os.path.join(
            root, "org/apache/commons/commons-lang3/maven-metadata.xml"
        )
        if not os.path.isfile(maven_meta_file):
            self.fail("maven-metadata is not generated correctly!")
        meta_doc = minidom.parse(maven_meta_file)
        groupId = meta_doc.getElementsByTagName("groupId")[0].firstChild.data
        self.assertEqual("org.apache.commons", groupId)
        artifactId = meta_doc.getElementsByTagName("artifactId")[0].firstChild.data
        self.assertEqual("commons-lang3", artifactId)
        versions = list(
            filter(
                lambda e: e.firstChild is not None,
                meta_doc.getElementsByTagName("versions")[0].childNodes,
            )
        )
        self.assertEqual(len(versions), 13)

        shutil.rmtree(temp_root)
