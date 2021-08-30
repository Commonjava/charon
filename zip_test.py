import os
import mrrc.archive as archive
import zipfile

def test():
  zip = zipfile.ZipFile(os.path.join(os.environ['HOME'],'temp/apache.zip'))

  archive.extract_zip_all(zip, '/tmp/tmp_zip/')
  # archive.extract_zip_with_files(zip, '/tmp/tmp_zip/', '.pom', debug=True)


if __name__ == '__main__':
  test()