import os
import shutil
import tempfile
from xml.dom import minidom
import zipfile
import mrrc.maven as mvn
import mrrc.archive as archive
from tests.base import BaseMRRCTest

class MavenMetadataTest(BaseMRRCTest):
    
    def test_parse_ga(self):
        g, a = mvn.parse_ga('org/apache/maven/plugins/maven-plugin-plugin', '')
        self.assertEqual('org.apache.maven.plugins', g)
        self.assertEqual('maven-plugin-plugin', a)
        g, a = mvn.parse_ga('/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin', '/tmp/maven-repository')
        self.assertEqual('org.apache.maven.plugins', g)
        self.assertEqual('maven-plugin-plugin', a)
    
    def test_parse_gavs(self):
        pom_paths = ['/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0.0/maven-plugin-plugin-1.0.0.pom',
                     '/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0.1/maven-plugin-plugin-1.0.1.pom',
                     '/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.2.0/maven-plugin-plugin-1.2.0.pom']
        parsed_gavs = mvn.parse_gavs(pom_paths, '/tmp/maven-repository')
        self.assertEqual(['1.0.0','1.0.1','1.2.0'], parsed_gavs['org.apache.maven.plugins']['maven-plugin-plugin'])
        
    def test_ver_cmp_key(self):
        comp_class = mvn.ver_cmp_key()
        self.assertLess(comp_class('1.0.0'), comp_class('1.0.1'))
        self.assertGreater(comp_class('1.10.0'), comp_class('1.9.1'))
        self.assertGreater(comp_class('1.0.1-alpha'), comp_class('1.0.1'))
        self.assertEqual(comp_class('1.0.1'), comp_class('1.0.1'))
        self.assertEqual(comp_class('1.0.1'), comp_class('1.0.1'))
        self.assertGreater(comp_class('2.0.1'), comp_class('1.0.1'))
        
    def test_gen_meta_file(self):
        zip = zipfile.ZipFile(os.path.join(os.getcwd(),'tests-input/commons-lang3.zip'))
        temp_root = os.path.join(self.tempdir, 'tmp_zip')
        os.mkdir(temp_root)
        archive.extract_zip_all(zip, temp_root)
        root = os.path.join(temp_root, 'apache-commons-maven-repository/maven-repository')
        poms = mvn.scan_for_poms(root)
        gav_dict = mvn.parse_gavs(poms, root)
        for g, avs in gav_dict.items():
            for a, vers in avs.items():
                mvn.gen_meta_file(g, a, vers, root)
        maven_meta_file = os.path.join(root, 'org/apache/commons/commons-lang3/maven-metadata.xml')
        if not os.path.isfile(maven_meta_file):
            self.fail("maven-metadata is not generated correctly!")
        meta_doc = minidom.parse(maven_meta_file)
        groupId = meta_doc.getElementsByTagName('groupId')[0].firstChild.data
        self.assertEqual('org.apache.commons', groupId)
        artifactId = meta_doc.getElementsByTagName('artifactId')[0].firstChild.data
        self.assertEqual('commons-lang3', artifactId)
        versions = list(filter(lambda e: e.firstChild is not None, meta_doc.getElementsByTagName('versions')[0].childNodes))
        self.assertEqual(len(versions), 13)
        
        shutil.rmtree(temp_root)