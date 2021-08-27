import mrrc.metadata_mvn as mvn
import os

def test():
  root = '/tmp/tmp_zip'
  poms = mvn.scan_for_poms('/tmp/tmp_zip/org/')
  gav_dict = mvn.parse_gavs(poms, root)
  for key, vers in gav_dict.items():
    print(mvn.gen_meta(key, vers).generate_meta_file_content())

if __name__ == '__main__':
  test()