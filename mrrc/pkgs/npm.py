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
from json import load, loads, dump, JSONDecodeError
from semantic_version import compare

from mrrc.s3.storage import S3Client
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


def store_package_metadata_to_S3(client: S3Client, path: str, target_dir: str, bucket: str,
                                 product: str):
    """ The main function to achieve the npm metadata merging then uploading against S3.
        The source package.json will be analyzed from the given single tarball path of input,
        Then go through S3 by the key: path and download the original to be merged package.json
        from S3
        if necessary. After merging, the result will be pushed into S3 update
    """
    package_metadata = get_package_metadata_from_archive(path, target_dir)
    result = package_metadata
    package_json_files = client.get_files(bucket_name=bucket, prefix=package_metadata.name,
                                          suffix=PACKAGE_JSON)
    if len(package_json_files) > 0:
        result = merge_package_metadata(package_metadata, client, bucket, package_json_files[0])
    full_path = __write_package_metadata_to_file(result, target_dir)
    client.upload_metadatas([full_path], bucket_name=bucket, product=product, root=target_dir)


def get_package_metadata_from_archive(path: str, target_dir: str) -> NPMPackageMetadata:
    """ Extract the tarball and re-locate the contents files based on npm structure.
        Get the version metadata object from this and then generate the package metadata
        from the version metadata
    """
    version_path = extract_npm_tarball(path, target_dir)
    version = scan_for_version(version_path)
    package = NPMPackageMetadata(version, True)
    return package


def merge_package_metadata(package_metadata: NPMPackageMetadata, client: S3Client, bucket: str,
                           key: str):
    """ If related package.json exists in S3, will download it from S3, then do the data merging
        of metadata.
        Some of the metadata need to validate the source package's version(single version so far),
        to determine the following merging action if it's the latest version
    """
    content = client.read_file_content(bucket, key)
    original = read_package_metadata_from_content(content)
    if original:
        source_version = list(package_metadata.versions.keys())[0]
        is_latest = __is_latest_version(source_version, list(original.versions.keys()))
        __do_merge(original, package_metadata, is_latest)
        return original


def gen_package_metadata_file(version_metadata: dict, target_dir: str):
    """ Give a version metadata and generate the package metadata based on that.
        The result will write the package metadata file to the appropriate path,
        e.g.: jquery/package.json or @types/jquery/package.json
        Root is like a prefix of the path which defaults to local repo location
    """
    package_metadata = NPMPackageMetadata(version_metadata, True)
    __write_package_metadata_to_file(package_metadata, target_dir)


def scan_for_version(path: str):
    """Scan a file path and find version metadata"""
    try:
        with open(path, encoding='utf-8') as version_meta_file:
            return load(version_meta_file)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')


def read_package_metadata_from_content(content: str) -> NPMPackageMetadata:
    """ Read the package metadata object from the object str content"""
    try:
        package_metadata = loads(content)
        return NPMPackageMetadata(package_metadata, False)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')


def __is_latest_version(source_version: str, versions: list()):
    for v in versions:
        if compare(source_version, v) <= 0:
            return False
    return True


def __do_merge(original: NPMPackageMetadata, source: NPMPackageMetadata, is_latest: bool):
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
            elif d in original.dist_tags.keys() and compare(source.dist_tags.get(d),
                                                            original.dist_tags.get(d)) > 0:
                original.dist_tags[d] = source.dist_tags.get(d)
                changed = True
    if source.versions:
        for v in source.versions.keys():
            original.versions[v] = source.versions.get(v)
            changed = True
    return changed


def __write_package_metadata_to_file(package_metadata: NPMPackageMetadata, root='/') -> str:
    logger.debug("NPM metadata will generate: %s", package_metadata)
    final_package_metadata_path = os.path.join(root, package_metadata.name, PACKAGE_JSON)
    try:
        with open(final_package_metadata_path, mode='w', encoding='utf-8') as f:
            dump(__del_none(package_metadata.__dict__.copy()), f)
        return final_package_metadata_path
    except FileNotFoundError:
        logger.error(
            'Can not create file %s because of some missing folders', final_package_metadata_path)


def __del_none(d):
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            __del_none(value)
    return d
