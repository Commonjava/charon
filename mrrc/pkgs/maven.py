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
from mrrc.utils.logs import DEFAULT_LOGGER
from mrrc.utils.files import write_file
from mrrc.utils.archive import extract_zip_all
from mrrc.storage.s3client import S3Client
from mrrc.config import MrrcConfig
from typing import Dict, List, Tuple
from jinja2 import Template
from datetime import datetime
from distutils.version import StrictVersion
from zipfile import ZipFile
from tempfile import mkdtemp
import os
import sys
import logging
import re

logger = logging.getLogger(DEFAULT_LOGGER)


class MavenMetadata(object):
    """This MavenMetadata will represent a maven-metadata.xml data content which will be
    used in jinja2 or other places
    """

    def __init__(self, group_id: str, artifact_id: str, versions: List[str]):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.last_upd_time = datetime.now().strftime("%Y%m%d%H%M%S")
        self.versions = versions
        self.sorted_versions = sorted(versions, key=StrictVersion)
        self._latest_version = None
        self._release_version = None

    def generate_meta_file_content(self) -> str:
        template = Template(get_mvn_template())
        return template.render(meta=self)

    @property
    def latest_version(self):
        if self._latest_version:
            return self._latest_version
        self._latest_version = self.sorted_versions[-1]
        return self._latest_version

    @property
    def release_version(self):
        if self._release_version:
            return self._release_version
        self._release_version = self.sorted_versions[-1]
        return self._release_version

    def __str__(self) -> str:
        return f"{self.group_id}:{self.artifact_id}\n{self.versions}\n\n"


def get_mvn_template() -> str:
    """Gets the jinja2 template file content for maven-metadata.xml generation"""
    DEFAULT_MVN_TEMPLATE = os.path.join(
        os.environ["HOME"], ".mrrc/template/maven-metadata.xml.j2"
    )
    with open(DEFAULT_MVN_TEMPLATE, encoding="utf-8") as file_:
        return file_.read()


def scan_for_poms(full_path: str) -> List[str]:
    """Scan a file path and finds all pom files absolute paths"""
    # collect poms
    all_pom_paths = list()
    for (directory, _, names) in os.walk(full_path):
        single_pom_paths = [
            os.path.join(directory, n) for n in names if n.endswith(".pom")
        ]
        all_pom_paths.extend(single_pom_paths)
    return all_pom_paths


def parse_ga(full_ga_path: str, root="/") -> Tuple[str, str]:
    """Parse maven groupId and artifactId from a standard path in a local maven repo.
    e.g: org/apache/maven/plugin/maven-plugin-plugin -> (org.apache.maven.plugin,
                                                         maven-plugin-plugin)
    root is like a prefix of the path which is not part of the maven GAV
    """
    slash_root = root
    if not root.endswith("/"):
        slash_root = slash_root + "/"

    ga_path = full_ga_path
    if ga_path.startswith(slash_root):
        ga_path = ga_path[len(slash_root):]
    if ga_path.endswith("/"):
        ga_path = ga_path[:-1]

    items = ga_path.split("/")
    artifact = items[len(items) - 1]
    group = ".".join(items[:-1])

    return group, artifact


def __parse_gav(full_artifact_path: str, root="/") -> Tuple[str, str, str]:
    """Parse maven groupId, artifactId and version from a standard path in a local maven repo.
    e.g: org/apache/maven/plugin/maven-plugin-plugin/1.0.0/maven-plugin-plugin-1.0.0.pom
    -> (org.apache.maven.plugin, maven-plugin-plugin, 1.0.0)
    root is like a prefix of the path which is not part of the maven GAV
    """
    slash_root = root
    if not root.endswith("/"):
        slash_root = slash_root + "/"

    ver_path = full_artifact_path
    if ver_path.startswith(slash_root):
        ver_path = ver_path[len(slash_root):]
    if ver_path.endswith("/"):
        ver_path = ver_path[:-1]

    items = ver_path.split("/")
    version = items[-2]
    artifact = items[-3]
    group = ".".join(items[:-3])

    return group, artifact, version


def parse_gavs(pom_paths: List[str], root="/") -> Dict[str, Dict[str, List[str]]]:
    """Give a list of paths with pom files and parse the maven groupId, artifactId and version
    from them. The result will be a dict like {groupId: {artifactId: [versions list]}}.
    Root is like a prefix of the path which is not part of the maven GAV
    """
    gavs = dict()
    for pom in pom_paths:
        (g, a, v) = __parse_gav(pom, root)
        avs = gavs.get(g, dict())
        vers = avs.get(a, list())
        vers.append(v)
        avs[a] = vers
        gavs[g] = avs
    return gavs


def gen_meta_file(group_id, artifact_id: str, versions: list, root="/") -> str:
    content = MavenMetadata(
        group_id, artifact_id, versions
    ).generate_meta_file_content()
    g_path = "/".join(group_id.split("."))
    final_meta_path = os.path.join(root, g_path, artifact_id, "maven-metadata.xml")
    try:
        write_file(final_meta_path, content)
    except FileNotFoundError as e:
        logger.error(
            "Error: Can not create file %s because of some missing folders",
            final_meta_path,
        )
        raise e
    return final_meta_path


def handle_maven_uploading(
    conf: MrrcConfig, repo: str, prod_key: str, ga: bool, bucket_name=None
):
    # 1. extract tarball
    logger.info("Extracting tarball %s", repo)
    repo_zip = ZipFile(repo)
    tmp_root = mkdtemp(prefix="mrrc-")
    extract_zip_all(repo_zip, tmp_root)

    # 2. scan for paths and filter out the ignored paths,
    # and also collect poms for later metadata generation
    logger.info("Scan %s to collect files", tmp_root)
    ignore_patterns = conf.get_ignore_patterns()
    top_level = "maven-repository"
    valid_paths, ignored_paths, valid_poms = [], [], []
    for root, dirs, names in os.walk(tmp_root):
        for directory in dirs:
            if directory == top_level:
                top_level = os.path.join(root, directory)
                break
        for name in names:
            path = os.path.join(root, name)
            if is_ignored(name, ignore_patterns):
                ignored_paths.append(name)
                continue
            valid_paths.append(path)
            if name.strip().endswith(".pom"):
                logger.debug("Found pom %s", name)
                valid_poms.append(path)
    logger.info("Files scanning done.\n")

    if ignore_patterns and len(ignore_patterns) > 0:
        logger.info(
            "Ignored paths with ignore_patterns %s as below:\n%s\n",
            ignore_patterns, "\n".join(ignored_paths)
        )

    # This prefix is a subdir under top-level directory in tarball
    # or root before real GAV dir structure
    if not os.path.isdir(top_level):
        logger.error("Error: the extracted top-level path %s does not exist.", top_level)
        sys.exit(1)

    # 3. do validation for the files, like product version checking
    logger.info("Validating paths with rules.")
    (err_msgs, passed) = validate_maven(valid_paths)
    if not passed:
        handle_error(err_msgs)
        # Question: should we exit here?

    # 4. Do uploading
    logger.info("Start uploading files to s3")
    s3_client = S3Client()
    bucket = bucket_name if bucket_name else conf.get_aws_bucket()
    s3_client.upload_files(
        file_paths=valid_paths, bucket_name=bucket, product=prod_key, root=top_level
    )
    logger.info("Files uploading done\n")

    # 5. Collect GAVs and generating maven-metadata.xml. As all valid poms has been
    # uploaded to s3 bucket, what we should do here is:
    # * Scan and get the GA for the uploaded poms this time
    # * Search all poms in s3 based on the GA
    # * Use searched poms to generate maven-metadata to refresh
    logger.info("Start generating maven-metadata.xml files for all artifacts")
    gas_dict = {}
    logger.debug("Valid poms: %s", valid_poms)
    valid_gavs_dict = parse_gavs(valid_poms, top_level)
    for g, avs in valid_gavs_dict.items():
        for a in avs.keys():
            logger.debug("G: %s, A: %s", g, a)
            g_path = "/".join(g.split("."))
            gas_dict[os.path.join(g_path, a)] = True
    all_poms = []
    for path, _ in gas_dict.items():
        poms = s3_client.get_files(bucket, path, ".pom")
        logger.debug("Got poms in s3 bucket %s for GA path %s: %s", bucket, path, poms)
        all_poms.extend(poms)
    gav_dict = parse_gavs(all_poms)
    meta_files = []
    for g, avs in gav_dict.items():
        for a, vers in avs.items():
            meta_file = gen_meta_file(g, a, vers, top_level)
            logger.debug("Generated metadata file %s for %s:%s", meta_file, g, a)
            meta_files.append(meta_file)
    logger.info("maven-metadata.xml files generation done\n")

    # 6. Upload all maven-metadata.xml
    logger.info("Start uploading maven-metadata.xml to s3")
    s3_client.upload_metadatas(
        meta_file_paths=meta_files, bucket_name=bucket, product=prod_key, root=top_level
    )
    logger.info("maven-metadata.xml uploading done")


def is_ignored(filename: str, ignore_patterns: List[str]) -> bool:
    if ignore_patterns:
        for dirs in ignore_patterns:
            if re.search(dirs, filename):
                return True
    return False


def validate_maven(paths: List[str]) -> Tuple[List[str], str]:
    # Reminder: need to implement later
    return (list(), True)


def handle_error(err_msgs: List[str]):
    # Reminder: will implement later
    pass
