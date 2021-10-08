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
from dataclasses import dataclass, field
from json import load, loads, dump, JSONDecodeError
from typing import Optional

from marshmallow import ValidationError
from marshmallow_dataclass import class_schema
from semantic_version import compare

from mrrc.storage.s3client import S3Client
from mrrc.utils.archive import extract_npm_tarball
from mrrc.utils.logs import DEFAULT_LOGGER

logger = logging.getLogger(DEFAULT_LOGGER)

PACKAGE_JSON = "package.json"


@dataclass
class NPMPackageMetadata(object):
    """This NPMPackageMetadata will represent the npm package(not version) package.json which will be
    used in jinja2 or other places
    """

    name: str
    dist_tags: Optional[dict] = field(default_factory=dict)
    versions: Optional[dict] = field(default_factory=dict)
    maintainers: Optional[list] = field(default_factory=list)
    description: Optional[str] = field(default="")
    time: Optional[dict] = field(default_factory=dict)
    author: Optional[str] = field(default="")
    users: Optional[dict] = field(default_factory=dict)
    repository: Optional[dict] = field(default_factory=dict)
    readme: Optional[str] = field(default="")
    readmeFilename: Optional[str] = field(default="")
    homepage: Optional[str] = field(default="")
    keywords: Optional[list] = field(default_factory=list)
    bugs: Optional[str] = field(default="")
    license: Optional[str] = field(default="")

    def get_name(self):
        return self.name

    def set_description(self, description: str):
        self.description = description
        return self

    def set_dist_tags(self, dist_tags: dict):
        self.dist_tags = dist_tags
        return self

    def set_versions(self, versions: dict):
        self.versions = versions
        return self

    def set_maintainers(self, maintainers: list):
        self.maintainers = maintainers
        return self

    def set_time(self, time: dict):
        self.time = time
        return self

    def set_author(self, author: str):
        self.author = author
        return self

    def set_users(self, users: dict):
        self.users = users
        return self

    def set_repository(self, repository: dict):
        self.repository = repository
        return self

    def set_readme(self, readme: str):
        self.readme = readme
        return self

    def set_readmeFilename(self, readmeFilename: str):
        self.readmeFilename = readmeFilename
        return self

    def set_homepage(self, homepage: str):
        self.homepage = homepage
        return self

    def set_keywords(self, keywords: list):
        self.keywords = keywords
        return self

    def set_bugs(self, bugs: str):
        self.bugs = bugs
        return self

    def set_license(self, _license: str):
        self.license = _license
        return self

    def __str__(self) -> str:
        return (
            f"{self.name}\n{self.description}\n{self.author}\n"
            f"{self.readme}\n{self.homepage}\n{self.license}\n\n"
        )


@dataclass
class NPMVersionMetadata:
    """This NPMVersionMetadata represents the npm version package.json"""

    name: str
    version: str
    title: Optional[str] = field(default="")
    description: Optional[str] = field(default="")
    main: Optional[str] = field(default="")
    url: Optional[str] = field(default="")
    homepage: Optional[str] = field(default="")
    keywords: Optional[list] = field(default_factory=list)
    author: Optional[str] = field(default="")
    contributors: Optional[list] = field(default_factory=list)
    maintainers: Optional[list] = field(default_factory=list)
    repository: Optional[dict] = field(default_factory=dict)
    bugs: Optional[str] = field(default="")
    license: Optional[str] = field(default="")
    dependencies: Optional[dict] = field(default_factory=dict)
    devDependencies: Optional[dict] = field(default_factory=dict)
    jsdomVersions: Optional[dict] = field(default_factory=dict)
    scripts: Optional[dict] = field(default_factory=dict)
    dist: Optional[dict] = field(default_factory=dict)
    directories: Optional[dict] = field(default_factory=dict)
    commitplease: Optional[dict] = field(default_factory=dict)
    engines: Optional[dict] = field(default_factory=dict)
    engineSupported: Optional[bool] = field(default="")
    files: Optional[list] = field(default_factory=list)
    deprecated: Optional[str] = field(default="")
    lib: Optional[str] = field(default="")
    gitHead: Optional[str] = field(default="")
    _shasum: Optional[str] = field(default="")
    _from: Optional[str] = field(default="")
    _npmVersion: Optional[str] = field(default="")
    _nodeVersion: Optional[str] = field(default="")
    _npmUser: Optional[dict] = field(default_factory=dict)
    _npmJsonOpts: Optional[dict] = field(default_factory=dict)
    _npmOperationalInternal: Optional[dict] = field(default_factory=dict)
    _defaultsLoaded: Optional[bool] = field(default="")
    publishConfig: Optional[dict] = field(default_factory=dict)
    _id: Optional[str] = field(default="")
    _hasShrinkwrap: Optional[bool] = field(default="")
    babel: Optional[dict] = field(default_factory=dict)

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_keywords(self):
        return self.keywords

    def get_description(self):
        return self.description

    def get_author(self):
        return self.author

    def get_license(self):
        return self.license

    def get_repository(self):
        return self.repository

    def get_bugs(self):
        return self.bugs

    def get_dist(self):
        return self.dist

    def get_maintainers(self):
        return self.maintainers

    def get_homepage(self):
        return self.homepage


def store_package_metadata_to_S3(client: S3Client, path: str, target_dir: str, bucket: str, product: str):
    """ The main function to achieve the npm metadata merging then uploading against S3.
        The source package.json will be analyzed from the given single tarball path of input,
        Then go through S3 by the key: path and download the original to be merged package.json from S3
        if necessary. After merging, the result will be pushed into S3 update
    """
    package_metadata = get_package_metadata_from_archive(path, target_dir)
    result = package_metadata
    package_prefix = package_metadata.get_name()
    package_json_files = client.get_files(bucket_name=bucket, prefix=package_prefix, suffix=PACKAGE_JSON)
    if len(package_json_files) > 0:
        result = merge_package_metadata(package_metadata, client, bucket, package_json_files[0])
    if result:
        write_package_metadata_to_S3(result, client, bucket, product, target_dir)


def get_package_metadata_from_archive(path: str, target_dir: str) -> NPMPackageMetadata:
    """ Extract the tarball and re-locate the contents files based on npm structure.
        Get the version metadata object from this and then generate the package metadata
        from the version metadata
    """
    version_path = extract_npm_tarball(path, target_dir)
    version = scan_for_version(version_path)
    package = __gen_package_metadata(version)
    return package


def merge_package_metadata(package_metadata: NPMPackageMetadata, client: S3Client, bucket: str, key: str):
    """ If related package.json exists in S3, will download it from S3, then do the data merging of metadata.
        Some of the metadata need to validate the source package's version(single version so far),
        to determine the following merging action if it's the latest version
    """
    content = client.read_file_content(bucket, key)
    original = read_package_metadata_from_content(content)
    if original:
        source_version = list(package_metadata.versions.keys())[0]
        is_latest = __is_latest_version(source_version, original.versions.keys())
        __do_merge(original, package_metadata, is_latest)
        return original


def write_package_metadata_to_S3(package_metadata: NPMPackageMetadata, client: S3Client, bucket: str, product: str,
                                 target_dir: str):
    """ Upload the merged package.json into S3
    """
    full_path = __write_package_metadata_to_file(package_metadata, target_dir)
    client.upload_metadatas([full_path], bucket_name=bucket, product=product, root=target_dir)


def gen_package_metadata_file(version_metadata: NPMVersionMetadata, target_dir: str):
    """ Give a version metadata and generate the package metadata based on that.
        The result will write the package metadata file to the appropriate path,
        e.g.: jquery/package.json or @types/jquery/package.json
        Root is like a prefix of the path which defaults to local repo location
    """
    package_metadata = __gen_package_metadata(version_metadata)
    __write_package_metadata_to_file(package_metadata, target_dir)


def scan_for_version(path: str) -> NPMVersionMetadata:
    """Scan a file path and find version metadata"""
    try:
        with open(path, encoding='utf-8') as version_meta_file:
            version_meta_data = load(version_meta_file)
        version_schema = class_schema(NPMVersionMetadata)()
        return version_schema.load(version_meta_data)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')
    except ValidationError:
        logger.error('Error: Failed to parse metadata by schema!')


def read_package_metadata_from_content(content: str) -> NPMPackageMetadata:
    """ Read the package metadata object from the object str content"""
    try:
        package_metadata = loads(content)
        package_schema = class_schema(NPMPackageMetadata)()
        return package_schema.load(package_metadata)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')
    except ValidationError:
        logger.error('Error: Failed to parse metadata by schema!')


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
            elif d in original.dist_tags.keys() and compare(source.dist_tags.get(d), original.dist_tags.get(d)) > 0:
                original.dist_tags[d] = source.dist_tags.get(d)
                changed = True
    if source.versions:
        for v in source.versions.keys():
            original.versions[v] = source.versions.get(v)
            changed = True
    return changed


def __gen_package_metadata(version_metadata: NPMVersionMetadata) -> NPMPackageMetadata:
    package_metadata = NPMPackageMetadata(version_metadata.get_name())
    if version_metadata.get_description():
        package_metadata.set_description(version_metadata.get_description())
    if version_metadata.get_author():
        package_metadata.set_author(version_metadata.get_author())
    if version_metadata.get_license():
        package_metadata.set_license(version_metadata.get_license())
    if version_metadata.get_repository():
        package_metadata.set_repository(version_metadata.get_repository())
    if version_metadata.get_bugs():
        package_metadata.set_bugs(version_metadata.get_bugs())
    if version_metadata.get_keywords():
        package_metadata.set_keywords(version_metadata.get_keywords())
    if version_metadata.maintainers:
        package_metadata.set_maintainers(version_metadata.get_maintainers())
    if version_metadata.homepage:
        package_metadata.set_homepage(version_metadata.get_homepage())

    tags_dict = dict()
    tags_dict["latest"] = version_metadata.get_version()
    package_metadata.set_dist_tags(tags_dict)

    version_dict = dict()
    version_dict[version_metadata.get_version()] = version_metadata.__dict__
    package_metadata.set_versions(version_dict)
    return package_metadata


def __write_package_metadata_to_file(package_metadata: NPMPackageMetadata, root='/') -> str:
    logger.debug("NPM metadata will generate: %s", package_metadata)
    final_package_metadata_path = os.path.join(root, package_metadata.get_name(), PACKAGE_JSON)
    try:
        with open(final_package_metadata_path, mode='w', encoding='utf-8') as f:
            dump(package_metadata.__dict__, f)
        return final_package_metadata_path
    except FileNotFoundError:
        logger.error(
            "Can not create file %s because of some missing folders",
            final_package_metadata_path,
        )
