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
from zipfile import ZipFile, is_zipfile
from json import load, JSONDecodeError
from enum import Enum
from typing import Tuple
import os
import sys
import tarfile
import logging

logger = logging.getLogger(__name__)


def extract_zip_all(zf: ZipFile, target_dir: str):
    zf.extractall(target_dir)


def extract_zip_with_files(zf: ZipFile, target_dir: str, file_suffix: str, debug=False):
    names = zf.namelist()
    filtered = list(filter(lambda n: n.endswith(file_suffix), names))
    if debug:
        logger.debug("Filtered files list as below with %s", file_suffix)
        for name in filtered:
            logger.debug(name)
    zf.extractall(target_dir, members=filtered)


def extract_npm_tarball(path: str, target_dir: str, is_for_upload: bool) -> Tuple[str, list]:
    """Extract npm tarball will relocate the tgz file and metadata files. locate the tar path (
    e.g.: jquery/-/jquery-7.6.1.tgz or @types/jquery/-/jquery-2.2.3.tgz), locate the version
    metadata path (e.g.: jquery/7.6.1 or @types/jquery/2.2.3). Result returns the version metadata
    file path for following package metadata generating operations
    """
    valid_paths = []
    package_name_path = str
    tgz = tarfile.open(path)
    tgz.extractall()
    for f in tgz:
        if f.name.endswith("package.json"):
            parse_paths = __parse_npm_package_version_paths(f.path)
            package_name_path = parse_paths[0]
            tarball_parent_path = os.path.join(target_dir, parse_paths[0], "-")
            valid_paths.append(os.path.join(tarball_parent_path, _get_tgz_name(path)))
            version_metadata_parent_path = os.path.join(
                target_dir, parse_paths[0], parse_paths[1]
            )
            valid_paths.append(os.path.join(version_metadata_parent_path, "package.json"))
            if is_for_upload:
                os.makedirs(tarball_parent_path)
                os.system("cp " + path + " " + tarball_parent_path)
                os.makedirs(version_metadata_parent_path)
                os.system(
                    "cp " + f.path + " " + version_metadata_parent_path
                )
            break
    return package_name_path, valid_paths


def _get_tgz_name(path: str):
    part = path.split("/")
    return part[len(part)-1]


def __parse_npm_package_version_paths(path: str) -> list:
    try:
        with open(path, encoding='utf-8') as version_package:
            data = load(version_package)
        package_version_paths = [data['name'], data['version']]
        return package_version_paths
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')


class NpmArchiveType(Enum):
    """Possible types of detected archive"""

    NOT_NPM = 0
    DIRECTORY = 1
    ZIP_FILE = 2
    TAR_FILE = 3


def detect_npm_archive(repo):
    """Detects, if the archive needs to have npm workflow.
    :parameter repo repository directory
    :return NpmArchiveType value
    """

    expanded_repo = os.path.expanduser(repo)
    if not os.path.exists(expanded_repo):
        logger.error("Repository %s does not exist!", expanded_repo)
        sys.exit(1)

    if os.path.isdir(expanded_repo):
        # we have archive repository
        repo_path = "".join((expanded_repo, "/package.json"))
        if os.path.isfile(repo_path):
            return NpmArchiveType.DIRECTORY
    elif is_zipfile(expanded_repo):
        # we have a ZIP file to expand
        with ZipFile(expanded_repo) as zz:
            try:
                if zz.getinfo("package.json"):
                    return NpmArchiveType.ZIP_FILE
            except KeyError:
                pass
    elif tarfile.is_tarfile(expanded_repo):
        with tarfile.open(expanded_repo) as tt:
            try:
                if tt.getmember("package/package.json").isfile():
                    return (
                        NpmArchiveType.TAR_FILE
                    )  # it is a tar file and has package.json in the right place
            except KeyError:
                pass

    return NpmArchiveType.NOT_NPM
