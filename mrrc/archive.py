from __future__ import print_function

import zipfile
import os


def extract_zip_all(zf: zipfile.ZipFile, target_dir: str):
    zf.extractall(target_dir)

def extract_zip_with_files(zf: zipfile.ZipFile, target_dir: str, file_suffix: str, debug=False):
    names = zf.namelist()
    filtered = list(filter(lambda n: n.endswith(file_suffix), names))
    if debug:
        print(f'Filtered files list as below with {file_suffix}')
        for name in filtered:
            print(name)
    zf.extractall(target_dir, members=filtered) 


