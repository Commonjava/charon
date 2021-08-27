from __future__ import print_function

import zipfile
import os

def iterate_zip_content(zf: zipfile.ZipFile, debug=False):
  zip_objects = zf.infolist()
  # Find which directory should be uploaded.
  repodir = _find_top_level(zip_objects)

  # Iterate over all objects in the directory.
  for info in zip_objects:
    if info.filename.endswith("/") and info.file_size == 0:
      # Skip directories for this iteration.
      continue

    filename = info.filename
    # We found maven-repository subdirectory previously, only content from
    # there should be taken.
    if repodir:
      if filename.startswith(repodir):
        # It's in correct location, move to top-level.
        filename = filename[len(repodir):]
      else:
        # Not correct location, ignore it.
        continue
    else:
      # Otherwise we only strip the leading component.
      filename = filename.split("/", 1)[-1]

    if debug:
      print("Mapping %s -> %s" % (info.filename, filename))
    yield filename, info.file_size, info.filename

def _find_top_level(zip_objects):
  repodir = None
  toplevel_objects = set()

  # Find if there is a maven-repository subdir under top-level directory.
  for info in zip_objects:
    parts = info.filename.split("/")
    toplevel_objects.add(parts[0])
    if len(parts) < 3:
      # Not a subdirectory of top-level dir or a file in there.
      continue
    if parts[1] == "maven-repository":
      repodir = os.path.join(*parts[:2]) + "/"

  if len(toplevel_objects) > 1:
    raise RuntimeError("Invalid zip file: there are multiple top-level entries.")

  return repodir

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


