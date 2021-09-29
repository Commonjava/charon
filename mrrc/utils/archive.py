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
import json
import logging
import os
import tarfile
from zipfile import ZipFile

logger = logging.getLogger(__name__)


def extract_zip_all(zf: ZipFile, target_dir: str):
    zf.extractall(target_dir)


def extract_zip_with_files(zf: ZipFile, target_dir: str, file_suffix: str, debug=False):
    names = zf.namelist()
    filtered = list(filter(lambda n: n.endswith(file_suffix), names))
    if debug:
        logger.debug('Filtered files list as below with %s', file_suffix)
        for name in filtered:
            logger.debug(name)
    zf.extractall(target_dir, members=filtered)


def extract_npm_tarball(path: str, target_dir: str) -> str:
    """ Extract npm tarball will relocate the tgz file and metadata files. locate the tar path (
    e.g.: jquery/-/jquery-7.6.1.tgz or @types/jquery/-/jquery-2.2.3.tgz), locate the version
    metadata path (e.g.: jquery/7.6.1 or @types/jquery/2.2.3) Result returns the version metadata
    file path for following package metadata generating operations
    """
    tgz = tarfile.open(path)
    tgz.extractall()
    for f in tgz:
        if f.name.endswith('package.json'):
            version_metadata_path = f.path
            parse_paths = __parse_npm_package_version_paths(f.path)

            tarball_parent_path = os.path.join(target_dir, parse_paths[0], '-')
            os.makedirs(tarball_parent_path)
            os.system('cp ' + path + ' ' + tarball_parent_path)

            version_metadata_parent_path = os.path.join(target_dir, parse_paths[0], parse_paths[1])
            os.makedirs(version_metadata_parent_path)
            os.system('cp ' + version_metadata_path + ' ' + version_metadata_parent_path)
            version_metadata_path = version_metadata_parent_path + '/package.json'
            break
    return version_metadata_path


def __parse_npm_package_version_paths(path: str) -> list:
    with open(path) as version_package:
        data = json.load(version_package)
    package_version_paths = [data['name'], data['version']]
    return package_version_paths
