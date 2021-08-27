import os
import mrrc.archive as archive
import zipfile

def test():
  zip = zipfile.ZipFile('/home/gli/temp/apache.zip')

  # items = archive.iterate_zip_content(zip)
  # for item in items:
  #   print(f'tripped={item[0]}, size={item[1]}, file={item[2]}')
  # filtered=list(filter(lambda i: (i[0].endswith('.pom')), items))
  # for filtered_item in filtered:
  #   print(f'tripped={filtered_item[0]}, size={filtered_item[1]}, file={filtered_item[2]}')
  
  archive.extract_zip_all(zip, '/tmp/tmp_zip/')
  # archive.extract_zip_with_files(zip, '/tmp/tmp_zip/', '.pom', debug=True)
  


if __name__ == '__main__':
  test()