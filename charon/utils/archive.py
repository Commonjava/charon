"""
Copyright (C) 2022 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
import logging
import os
import sys
import tarfile
import requests
import tempfile
import shutil
import subresource_integrity
from enum import Enum
from json import load, JSONDecodeError, dump
from typing import Tuple
from zipfile import ZipFile, is_zipfile
from charon.constants import DEFAULT_REGISTRY
from charon.utils.files import digest, HashType
from charon.utils.map import del_none

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


def extract_npm_tarball(
    path: str, target_dir: str, is_for_upload: bool, pkg_root="package", registry=DEFAULT_REGISTRY
) -> Tuple[str, list]:
    """ Extract npm tarball will relocate the tgz file and metadata files.
        * Locate tar path ( e.g.: jquery/-/jquery-7.6.1.tgz or @types/jquery/-/jquery-2.2.3.tgz).
        * Locate version metadata path (e.g.: jquery/7.6.1 or @types/jquery/2.2.3).
        Result returns the version meta file path and is for following package meta generating.
    """
    valid_paths = []
    package_name_path = str()
    tgz = tarfile.open(path)
    pkg_file = None
    root_pkg_file_exists = True
    try:
        root_pkg_path = os.path.join(pkg_root, "package.json")
        logger.debug(root_pkg_path)
        pkg_file = tgz.getmember(root_pkg_path)
        root_pkg_file_exists = pkg_file.isfile()
    except KeyError:
        root_pkg_file_exists = False
        pkg_file = None
    tgz.extractall()
    if not root_pkg_file_exists:
        logger.info(
            "Root package.json is not found for archive: %s, will search others",
            path
        )
        for f in tgz:
            if f.name.endswith("package.json"):
                logger.info("Found package.json as %s", f.path)
                pkg_file = f
                break
    if pkg_file:
        version_data, parse_paths = __parse_npm_package_version_paths(pkg_file.path)
        package_name_path = parse_paths[0]
        os.makedirs(os.path.join(target_dir, parse_paths[0]))
        tarball_parent_path = os.path.join(target_dir, parse_paths[0], "-")
        valid_paths.append(os.path.join(tarball_parent_path, _get_tgz_name(path)))
        version_metadata_parent_path = os.path.join(
            target_dir, parse_paths[0], parse_paths[1]
        )
        valid_paths.append(os.path.join(version_metadata_parent_path, "package.json"))

        if is_for_upload:
            tgz_relative_path = "/".join([parse_paths[0], "-", _get_tgz_name(path)])
            __write_npm_version_dist(
                path, pkg_file.path, version_data, tgz_relative_path, registry
            )

            os.makedirs(tarball_parent_path)
            target = os.path.join(tarball_parent_path, os.path.basename(path))
            shutil.copyfile(path, target)
            os.makedirs(version_metadata_parent_path)
            target = os.path.join(version_metadata_parent_path, os.path.basename(pkg_file.path))
            shutil.copyfile(pkg_file.path, target)
    return package_name_path, valid_paths


def _get_tgz_name(path: str):
    parts = path.split("/")
    if len(parts) > 0:
        return parts[-1]
    return ""


def __write_npm_version_dist(path: str, version_meta_extract_path: str, version_data: dict,
                             tgz_relative_path: str, registry: str):
    dist = dict()
    dist["tarball"] = "".join(["https://", registry, "/", tgz_relative_path])
    dist["shasum"] = digest(path, HashType.SHA1)
    with open(path, "rb") as tarball:
        tarball_data = tarball.read()
        integrity = subresource_integrity.render(tarball_data, ['sha512'])
        dist["integrity"] = integrity
    version_data["dist"] = dist
    with open(version_meta_extract_path, mode='w', encoding='utf-8') as f:
        dump(del_none(version_data), f)


def __parse_npm_package_version_paths(path: str) -> Tuple[dict, list]:
    try:
        with open(path, encoding='utf-8') as version_package:
            data = load(version_package)
        package_version_paths = [data['name'], data['version']]
        return data, package_version_paths
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


def download_archive(url: str, base_dir=None) -> str:
    dir_ = base_dir
    if not dir_ or not os.path.isdir(dir_):
        dir_ = tempfile.mkdtemp()
        logger.info("No base dir specified for holding archive."
                    " Will use a temp dir %s to hold archive",
                    dir_)
    # Used solution here:
    # https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
    local_filename = os.path.join(dir_, url.split('/')[-1])
    # NOTE the stream=True parameter below
    # NOTE(2) timeout=30 parameter to set a 30-second timeout, and prevent indefinite hang.
    with requests.get(url, stream=True, timeout=30, verify=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)
    return local_filename
