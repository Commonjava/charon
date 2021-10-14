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
import logging
import os
import re
import sys
from json import load, loads, dump, JSONDecodeError
from tempfile import mkdtemp
from typing import Tuple

from semantic_version import compare

from mrrc.config import AWS_DEFAULT_BUCKET
from mrrc.constants import META_FILE_GEN_KEY, META_FILE_DEL_KEY
from mrrc.storage import S3Client
from mrrc.utils.archive import extract_npm_tarball

logger = logging.getLogger(__name__)

PACKAGE_JSON = "package.json"


class NPMPackageMetadata(object):
    """ This NPMPackageMetadata will represent the npm package(not version) package.json which will
        be used in jinja2 or other places.
    """

    def __init__(self, metadata, is_version):
        self.name = metadata.get('name', None)
        self.description = metadata.get('description', None)
        self.author = metadata.get('author', None)
        self.license = metadata.get('license', None)
        self.repository = metadata.get('repository', None)
        self.bugs = metadata.get('bugs', None)
        self.keywords = metadata.get('keywords', None)
        self.maintainers = metadata.get('maintainers', None)
        self.users = metadata.get('users', None)
        self.homepage = metadata.get('homepage', None)
        self.time = metadata.get('time', None)
        self.readme = metadata.get('readme', None)
        self.readmeFilename = metadata.get('readmeFilename', None)
        if is_version:
            self.dist_tags = {'latest': metadata.get('version')}
            self.versions = {metadata.get('version'): metadata}
        else:
            self.dist_tags = metadata.get('dist_tags', None)
            self.versions = metadata.get('versions', None)


def handle_npm_uploading(
        tarball_path: str, product: str, bucket_name=None, dir_=None
):
    """ The main function to achieve the npm metadata merging then uploading against S3.
        The source package.json will be analyzed from the given single tarball path of input,
        Then go through S3 by the key: path and download the original to be merged package.json
        from S3
        if necessary. After merging, the result will be pushed into S3 update
    """
    target_dir, valid_paths, package_metadata = _scan_metadata_paths_from_archive(
        tarball_path, prefix=product, dir__=dir_
    )
    if not os.path.isdir(target_dir):
        logger.error("Error: the extracted target_dir path %s does not exist.", target_dir)
        sys.exit(1)

    client = S3Client()
    bucket = bucket_name if bucket_name else AWS_DEFAULT_BUCKET
    client.upload_files(
        file_paths=valid_paths, bucket_name=bucket, product=product, root=target_dir
    )
    meta_files = _gen_npm_package_metadata(
        client, bucket, target_dir, package_metadata.name, source_package=package_metadata
    )
    if META_FILE_GEN_KEY in meta_files:
        client.upload_metadatas(
            meta_file_paths=[meta_files[META_FILE_GEN_KEY]],
            bucket_name=bucket,
            product=product,
            root=target_dir
        )


def handle_npm_del(
        tarball_path: str, product: str, bucket_name=None, dir_=None
):
    target_dir, package_name_path, valid_paths = _scan_paths_from_archive(
        tarball_path, prefix=product, dir__=dir_
    )

    client = S3Client()
    bucket = bucket_name if bucket_name else AWS_DEFAULT_BUCKET
    client.delete_files(
        file_paths=valid_paths, bucket_name=bucket, product=product, root=target_dir
    )
    meta_files = _gen_npm_package_metadata(client, bucket, target_dir, package_name_path)
    all_meta_files = []
    for _, file in meta_files.items():
        all_meta_files.append(file)
    client.delete_files(
        file_paths=all_meta_files, bucket_name=bucket, product=product, root=target_dir
    )
    if META_FILE_GEN_KEY in meta_files:
        client.upload_metadatas(
            meta_file_paths=[meta_files[META_FILE_GEN_KEY]],
            bucket_name=bucket,
            product=None,
            root=target_dir
        )


def _gen_npm_package_metadata(
        client: S3Client, bucket: str, target_dir: str, package_path_prefix: str,
        source_package: NPMPackageMetadata = None
) -> dict:
    meta_files = {}
    package_metadata_key = os.path.join(package_path_prefix, PACKAGE_JSON)
    # for upload mode, source_package is not None
    if source_package:
        package_json_files = client.get_files(bucket_name=bucket, prefix=package_metadata_key)
        result = source_package
        if len(package_json_files) > 0:
            result = _merge_package_metadata(
                source_package, client, bucket, package_json_files[0]
            )
        meta_file = _write_package_metadata_to_file(result, target_dir)
        meta_files[META_FILE_GEN_KEY] = meta_file
        return meta_files

    # for delete mode
    existed_version_metas = client.get_files(
        bucket_name=bucket, prefix=package_path_prefix, suffix=PACKAGE_JSON
    )
    existed_version_metas.remove(package_metadata_key)
    if len(existed_version_metas) > 0:
        meta_contents = list()
        for key in existed_version_metas:
            content = client.read_file_content(bucket, key)
            meta = read_package_metadata_from_content(content, True)
            if not meta:
                continue
            meta_contents.append(meta)
        if len(meta_contents) == 0:
            return
        original = meta_contents[0]
        for source in meta_contents:
            source_version = list(source.versions.keys())[0]
            is_latest = _is_latest_version(source_version, list(original.versions.keys()))
            _do_merge(original, source, is_latest)
        meta_file = _write_package_metadata_to_file(original, target_dir)
        meta_files[META_FILE_GEN_KEY] = meta_file
    else:
        meta_files[META_FILE_DEL_KEY] = package_metadata_key
    return meta_files


def _scan_metadata_paths_from_archive(path: str, prefix="", dir__=None) -> Tuple[str, list, NPMPackageMetadata]:
    """ Extract the tarball and re-locate the contents files based on npm structure.
        Get the version metadata object from this and then generate the package metadata
        from the version metadata
    """
    tmp_root = mkdtemp(prefix=f"npm-mrrc-{prefix}-", dir=dir__)
    package_name_path, valid_paths = extract_npm_tarball(path, tmp_root, True)
    if len(valid_paths) > 1:
        version = scan_for_version(valid_paths[1])
        package = NPMPackageMetadata(version, True)
    return tmp_root, valid_paths, package


def _scan_paths_from_archive(path: str, prefix="", dir__=None) -> Tuple[str, str, list]:
    tmp_root = mkdtemp(prefix=f"npm-mrrc-{prefix}-", dir=dir__)
    package_name_path, valid_paths = extract_npm_tarball(path, tmp_root, False)
    return tmp_root, package_name_path, valid_paths


def _merge_package_metadata(
        package_metadata: NPMPackageMetadata, client: S3Client, bucket: str,
        key: str
):
    """ If related package.json exists in S3, will download it from S3, then do the data merging
        of metadata.
        Some of the metadata need to validate the source package's version(single version so far),
        to determine the following merging action if it's the latest version
    """
    content = client.read_file_content(bucket, key)
    original = read_package_metadata_from_content(content, False)

    if original:
        source_version = list(package_metadata.versions.keys())[0]
        is_latest = _is_latest_version(source_version, list(original.versions.keys()))
        _do_merge(original, package_metadata, is_latest)
        return original


def gen_package_metadata_file(version_metadata: dict, target_dir: str):
    """ Give a version metadata and generate the package metadata based on that.
        The result will write the package metadata file to the appropriate path,
        e.g.: jquery/package.json or @types/jquery/package.json
        Root is like a prefix of the path which defaults to local repo location
    """
    package_metadata = NPMPackageMetadata(version_metadata, True)
    _write_package_metadata_to_file(package_metadata, target_dir)


def scan_for_version(path: str):
    """Scan a file path and find version metadata"""
    try:
        with open(path, encoding='utf-8') as version_meta_file:
            return load(version_meta_file)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')


def read_package_metadata_from_content(content: str, is_version) -> NPMPackageMetadata:
    """ Read the package metadata object from the object str content"""
    try:
        package_metadata = loads(content)
        return NPMPackageMetadata(package_metadata, is_version)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')


def _is_latest_version(source_version: str, versions: list()):
    for v in versions:
        if compare(source_version, v) <= 0:
            return False
    return True


def _do_merge(original: NPMPackageMetadata, source: NPMPackageMetadata, is_latest: bool):
    changed = False
    if is_latest:
        if source.name:
            original.name = source.name
            changed = True
        if source.description:
            original.description = source.description
            changed = True
        if source.author:
            original.author = source.author
            changed = True
        if source.readme:
            original.readme = source.readme
            changed = True
        if source.readmeFilename:
            original.readmeFilename = source.readmeFilename
            changed = True
        if source.homepage:
            original.homepage = source.homepage
            changed = True
        if source.bugs:
            original.bugs = source.bugs
            changed = True
        if source.license:
            original.license = source.license
            changed = True
        if source.repository and len(source.repository) > 0:
            original.repository = source.repository
            changed = True
    if source.maintainers:
        for m in source.maintainers:
            if m not in original.maintainers:
                original.maintainers.append(m)
                changed = True
    if source.keywords:
        for k in source.keywords:
            if k not in original.keywords:
                original.keywords.append(k)
                changed = True
    if source.users:
        for u in source.users.keys():
            original.users[u] = source.users.get(u)
            changed = True
    if source.time:
        for t in source.time.keys():
            original.time[t] = source.time.get(t)
            changed = True
    if source.dist_tags:
        for d in source.dist_tags.keys():
            if d not in original.dist_tags.keys():
                original.dist_tags[d] = source.dist_tags.get(d)
                changed = True
            elif d in original.dist_tags.keys() and compare(
                    source.dist_tags.get(d),
                    original.dist_tags.get(d)
            ) > 0:
                original.dist_tags[d] = source.dist_tags.get(d)
                changed = True
    if source.versions:
        for v in source.versions.keys():
            original.versions[v] = source.versions.get(v)
            changed = True
    return changed


def _write_package_metadata_to_file(package_metadata: NPMPackageMetadata, root='/') -> str:
    logger.debug("NPM metadata will generate: %s", package_metadata)
    final_package_metadata_path = os.path.join(root, package_metadata.name, PACKAGE_JSON)
    try:
        with open(final_package_metadata_path, mode='w', encoding='utf-8') as f:
            dump(_del_none(package_metadata.__dict__.copy()), f)
        return final_package_metadata_path
    except FileNotFoundError:
        logger.error(
            'Can not create file %s because of some missing folders', final_package_metadata_path
        )


def _del_none(d):
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            _del_none(value)
    return d
