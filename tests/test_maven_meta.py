import mrrc.metadata_mvn as mvn
from .base import BaseMRRCTest

class MavenMetadataTest(BaseMRRCTest):
    # def test(self):
    #     root = '/tmp/tmp_zip'
    #     poms = mvn.scan_for_poms('/tmp/tmp_zip/')
    #     gav_dict = mvn.parse_gavs(poms, root)
    #     for key, vers in gav_dict.items():
    #         print(mvn.gen_meta(key, vers).generate_meta_file_content())
    
    def test_parse_ga(self):
        g, a = mvn.parse_ga('org/apache/maven/plugins/maven-plugin-plugin', '')
        self.assertEqual('org.apache.maven.plugins', g)
        self.assertEqual('maven-plugin-plugin', a)
        g, a = mvn.parse_ga('/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin', '/tmp/maven-repository')
        self.assertEqual('org.apache.maven.plugins', g)
        self.assertEqual('maven-plugin-plugin', a)
    
    # def test_parse_gav(self):
    #     g, a, v = mvn.parse_gav('org/apache/maven/plugins/maven-plugin-plugin/1.0/maven-plugin-plugin-1.0.pom', '')
    #     self.assertEqual('org.apache.maven.plugins', g)
    #     self.assertEqual('maven-plugin-plugin', a)
    #     self.assertEqual('1.0', v)
    #     g, a, v = mvn.parse_gav('/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0/maven-plugin-plugin-1.0.pom', '/tmp/maven-repository')
    #     self.assertEqual('org.apache.maven.plugins', g)
    #     self.assertEqual('maven-plugin-plugin', a)
    #     self.assertEqual('1.0', v)
    
    def test_parse_gavs(self):
        pom_paths = ['/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0.0/maven-plugin-plugin-1.0.0.pom',
                     '/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.0.1/maven-plugin-plugin-1.0.1.pom',
                     '/tmp/maven-repository/org/apache/maven/plugins/maven-plugin-plugin/1.2.0/maven-plugin-plugin-1.2.0.pom']
        parsed_gavs = mvn.parse_gavs(pom_paths, '/tmp/maven-repository')
        self.assertEqual(['1.0.0','1.0.1','1.2.0'], parsed_gavs['org.apache.maven.plugins.maven-plugin-plugin'])
        
    def test_ver_cmp_key(self):
        comp_class = mvn.ver_cmp_key()
        self.assertLess(comp_class('1.0.0'), comp_class('1.0.1'))
        self.assertGreater(comp_class('1.10.0'), comp_class('1.9.1'))
        self.assertGreater(comp_class('1.0.1-alpha'), comp_class('1.0.1'))
        self.assertEqual(comp_class('1.0.1'), comp_class('1.0.1'))
        self.assertEqual(comp_class('1.0.1'), comp_class('1.0.1'))
        self.assertGreater(comp_class('2.0.1'), comp_class('1.0.1'))