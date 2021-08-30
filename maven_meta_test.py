from mrrc.metadata_mvn import MavenMetadata

def test():
  meta = MavenMetadata("org.commonjava.indy", "indy-api").\
    latest_version("2.0.0").release_version("1.9.9").\
    versions("1.0.0", "1.0.1", "1.1.0", "1.2.0", "1.5.0", "1.7.0", \
    "1.9.0", "1.9.9", "2.0.0")
  print(meta.generate_meta_file_content())
  
if __name__ == '__main__':
  test()