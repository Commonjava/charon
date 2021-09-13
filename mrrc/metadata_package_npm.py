import os
from jinja2 import Template
from typing import Optional
from dataclasses import dataclass, field
from mrrc.metadata_version_npm import NPMVersionMetadata


@dataclass
class NPMPackageMetadata(object):
    """ This NPMPackageMetadata will represent the npm package(not version) package.json which will be
        used in jinja2 or other places
    """

    def generate_meta_file_content(self) -> str:
        template = Template(get_npm_template())
        return template.render(meta=self)

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


def logging(msg):
    # TODO: Will use logging libs instead later
    print(msg)


def get_npm_template() -> str:
    """Gets the jinja2 template file content for package.json generation
    """
    DEFAULT_NPM_TEMPLATE = os.path.join(os.environ['HOME'], '.mrrc/template/package.json.j2')
    with open(DEFAULT_NPM_TEMPLATE) as file_:
        return file_.read()


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
    version_dict[version_metadata.get_version()] = version_metadata
    package_metadata.set_versions(version_dict)

    logging(package_metadata.__str__())

    final_package_metadata_path = os.path.join(root, package_metadata.get_name(), 'package.json')
    try:
        write_file(final_package_metadata_path, package_metadata.generate_meta_file_content())
    except FileNotFoundError:
        logging(f'Can not create file {final_package_metadata_path} because of some missing folders')


def write_file(file_path: str, content: str):
    if not os.path.isfile(file_path):
        with open(file_path, mode='a'):
            pass
    with open(file_path, mode='w') as f:
        f.write(content)
