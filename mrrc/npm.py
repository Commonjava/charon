from mrrc.logs import DEFAULT_LOGGER
from typing import Optional
from dataclasses import dataclass, field
from marshmallow import ValidationError
import os
import json
import marshmallow_dataclass
import logging


logger = logging.getLogger(DEFAULT_LOGGER)

@dataclass
class NPMPackageMetadata(object):
    """ This NPMPackageMetadata will represent the npm package(not version) package.json which will be
        used in jinja2 or other places
    """
    name: str
    dist_tags: Optional[dict] = field(default_factory=dict)
    versions: Optional[dict] = field(default_factory=dict)
    maintainers: Optional[list] = field(default_factory=list)
    description: Optional[str] = field(default='')
    time: Optional[dict] = field(default_factory=dict)
    author: Optional[str] = field(default='')
    users: Optional[dict] = field(default_factory=dict)
    repository: Optional[dict] = field(default_factory=dict)
    readme: Optional[str] = field(default='')
    readmeFilename: Optional[str] = field(default='')
    homepage: Optional[str] = field(default='')
    keywords: Optional[list] = field(default_factory=list)
    bugs: Optional[str] = field(default='')
    license: Optional[str] = field(default='')

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

    def set_bugs(self, bugs: dict):
        self.bugs = bugs
        return self

    def set_license(self, license: str):
        self.license = license
        return self

    def __str__(self) -> str:
        return f'{self.name}\n{self.description}\n{self.author}\n{self.readme}\n{self.homepage}\n{self.license}\n\n'


@dataclass
class NPMVersionMetadata:
    """ This NPMVersionMetadata represents the npm version package.json
    """
    name: str
    version: str
    title: Optional[str] = field(default='')
    description: Optional[str] = field(default='')
    main: Optional[str] = field(default='')
    url: Optional[str] = field(default='')
    homepage: Optional[str] = field(default='')
    keywords: Optional[list] = field(default_factory=list)
    author: Optional[str] = field(default='')
    contributors: Optional[list] = field(default_factory=list)
    maintainers: Optional[list] = field(default_factory=list)
    repository: Optional[dict] = field(default_factory=dict)
    bugs: Optional[str] = field(default='')
    license: Optional[str] = field(default='')
    dependencies: Optional[dict] = field(default_factory=dict)
    devDependencies: Optional[dict] = field(default_factory=dict)
    jsdomVersions: Optional[dict] = field(default_factory=dict)
    scripts: Optional[dict] = field(default_factory=dict)
    dist: Optional[dict] = field(default_factory=dict)
    directories: Optional[dict] = field(default_factory=dict)
    commitplease: Optional[dict] = field(default_factory=dict)
    engines: Optional[dict] = field(default_factory=dict)
    engineSupported: Optional[bool] = field(default='')
    files: Optional[list] = field(default_factory=list)
    deprecated: Optional[str] = field(default='')
    lib: Optional[str] = field(default='')
    gitHead: Optional[str] = field(default='')
    _shasum: Optional[str] = field(default='')
    _from: Optional[str] = field(default='')
    _npmVersion: Optional[str] = field(default='')
    _nodeVersion: Optional[str] = field(default='')
    _npmUser: Optional[dict] = field(default_factory=dict)
    _npmJsonOpts: Optional[dict] = field(default_factory=dict)
    _npmOperationalInternal: Optional[dict] = field(default_factory=dict)
    _defaultsLoaded: Optional[bool] = field(default='')
    publishConfig: Optional[dict] = field(default_factory=dict)
    _id: Optional[str] = field(default='')
    _hasShrinkwrap: Optional[bool] = field(default='')
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


def scan_for_version(path: str) -> NPMVersionMetadata:
    """Scan a file path and find version metadata
    """
    try:
        with open(path) as version_meta_file:
            version_meta_data = json.load(version_meta_file)
        version_schema = marshmallow_dataclass.class_schema(NPMVersionMetadata)()
        return version_schema.load(version_meta_data)
    except ValidationError:
        logger.error('Error: Failed to validate version metadata!')


def gen_package_meatadata_file(version_metadata: NPMVersionMetadata, root='/'):
    """Give a version metadata and generate the package metadata based on that.
       The result will write the package metadata file to the appropriate path,
       e.g.: jquery/package.json or @types/jquery/package.json
       Root is like a prefix of the path which defaults to local repo location
    """
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
    tags_dict['latest'] = version_metadata.get_version()
    package_metadata.set_dist_tags(tags_dict)

    version_dict = dict()
    version_dict[version_metadata.get_version()] = version_metadata.__dict__
    package_metadata.set_versions(version_dict)

    logger.debug(f'NPM metadata will generate: {package_metadata}')
    final_package_metadata_path = os.path.join(root, package_metadata.get_name(), 'package.json')
    try:
        with open(final_package_metadata_path, mode='w') as f:
            json.dump(package_metadata.__dict__, f)
    except FileNotFoundError:
        logger.error(f'Can not create file {final_package_metadata_path} because of some missing folders')