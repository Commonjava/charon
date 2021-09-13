import json
import marshmallow_dataclass
from typing import Optional
from dataclasses import dataclass
from marshmallow import ValidationError


@dataclass
class NPMVersionMetadata:
    """ This NPMVersionMetadata represents the npm version package.json
    """
    name: str
    version: str
    title: Optional[str]
    description: Optional[str]
    main: Optional[str]
    url: Optional[str]
    homepage: Optional[str]
    keywords: Optional[list]
    author: Optional[str]
    contributors: Optional[list]
    maintainers: Optional[list]
    repository: Optional[dict]
    bugs: Optional[str]
    license: Optional[str]
    dependencies: Optional[dict]
    devDependencies: Optional[dict]
    jsdomVersions: Optional[dict]
    scripts: Optional[dict]
    dist: Optional[dict]
    directories: Optional[dict]
    commitplease: Optional[dict]
    engines: Optional[dict]
    engineSupported: Optional[bool]
    files: Optional[list]
    deprecated: Optional[str]
    lib: Optional[str]
    gitHead: Optional[str]
    _shasum: Optional[str]
    _from: Optional[str]
    _npmVersion: Optional[str]
    _nodeVersion: Optional[str]
    _npmUser: Optional[dict]
    _npmJsonOpts: Optional[dict]
    _npmOperationalInternal: Optional[dict]
    _defaultsLoaded: Optional[bool]
    publishConfig: Optional[dict]
    _id: Optional[str]
    _hasShrinkwrap: Optional[bool]
    babel: Optional[dict]

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


def logging(msg):
    # TODO: Will use logging libs instead later
    print(msg)


def scan_for_version(path: str) -> NPMVersionMetadata:
    """Scan a file path and find version metadata
    """
    try:
        with open(path) as version_meta_file:
            version_meta_data = json.load(version_meta_file)
        version_schema = marshmallow_dataclass.class_schema(NPMVersionMetadata)()
        version = version_schema.load(version_meta_data)
        return version
    except ValidationError:
        logging('Error: Failed to validate version metadata!')