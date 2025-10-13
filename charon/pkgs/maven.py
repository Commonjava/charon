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
from charon.utils.files import HashType
import charon.pkgs.indexing as indexing
import charon.pkgs.signature as signature
from charon.utils.files import overwrite_file, digest, write_manifest
from charon.utils.archive import extract_zip_all
from charon.utils.strings import remove_prefix
from charon.storage import S3Client
from charon.cache import CFClient
from charon.types import TARGET_TYPE
from charon.pkgs.pkg_utils import (
    upload_post_process,
    rollback_post_process,
    invalidate_cf_paths
)
from charon.config import CharonConfig, get_template, get_config
from charon.constants import (META_FILE_GEN_KEY, META_FILE_DEL_KEY,
                              META_FILE_FAILED, MAVEN_METADATA_TEMPLATE,
                              ARCHETYPE_CATALOG_TEMPLATE, ARCHETYPE_CATALOG_FILENAME,
                              PACKAGE_TYPE_MAVEN)
from typing import Dict, List, Tuple, Union
from jinja2 import Template
from datetime import datetime
from zipfile import ZipFile, BadZipFile
from tempfile import mkdtemp
from shutil import rmtree, copy2
from defusedxml import ElementTree

import os
import sys
import logging
import re

logger = logging.getLogger(__name__)


def __get_mvn_template(kind: str, default: str) -> str:
    """Gets the jinja2 template file content for metadata generation"""
    try:
        return get_template(kind)
    except FileNotFoundError:
        logger.info("%s template file not defined,"
                    " will use default template.", kind)
        return default


META_TEMPLATE = __get_mvn_template("maven-metadata.xml.j2", MAVEN_METADATA_TEMPLATE)
ARCH_TEMPLATE = __get_mvn_template("archetype-catalog.xml.j2", ARCHETYPE_CATALOG_TEMPLATE)
MAVEN_METADATA_FILE = "maven-metadata.xml"
MAVEN_ARCH_FILE = "archetype-catalog.xml"
STANDARD_GENERATED_IGNORES = [MAVEN_METADATA_FILE, MAVEN_ARCH_FILE]


class MavenMetadata(object):
    """This MavenMetadata will represent a maven-metadata.xml data content which will be
    used in jinja2 or other places
    """

    def __init__(self, group_id: str, artifact_id: str, versions: List[str]):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.last_upd_time = datetime.now().strftime("%Y%m%d%H%M%S")
        self.versions = sorted(set(versions), key=VersionCompareKey)
        self._latest_version = None
        self._release_version = None

    def generate_meta_file_content(self) -> str:
        template = Template(META_TEMPLATE)
        return template.render(meta=self)

    @property
    def latest_version(self):
        if self._latest_version:
            return self._latest_version
        self._latest_version = self.versions[-1]
        return self._latest_version

    @property
    def release_version(self):
        if self._release_version:
            return self._release_version
        self._release_version = self.versions[-1]
        return self._release_version

    def __str__(self) -> str:
        return f"{self.group_id}:{self.artifact_id}\n{self.versions}\n\n"


class ArchetypeRef(object):
    """This ArchetypeRef will represent an entry in archetype-catalog.xml content which will be
    used in jinja2 or other places
    """

    def __init__(self, group_id: str, artifact_id: str, version: str, description: str):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.description = description

    def __hash__(self):
        return hash(self.group_id + self.artifact_id + self.version)

    def __eq__(self, other) -> bool:
        if isinstance(other, ArchetypeRef):
            return self.group_id == other.group_id \
                   and self.artifact_id == other.artifact_id \
                   and self.version == other.version

        return False

    def __str__(self) -> str:
        return f"{self.group_id}:{self.artifact_id}\n{self.version}\n{self.description}\n\n"


class MavenArchetypeCatalog(object):
    """This MavenArchetypeCatalog represents an archetype-catalog.xml which will be
    used in jinja2 to regenerate the file with merged contents
    """

    def __init__(self, archetypes: List[ArchetypeRef]):
        self.archetypes = sorted(set(archetypes), key=ArchetypeCompareKey)

    def generate_meta_file_content(self) -> str:
        template = Template(ARCHETYPE_CATALOG_TEMPLATE)
        return template.render(archetypes=self.archetypes)

    def __str__(self) -> str:
        return f"(Archetype Catalog with {len(self.archetypes)} entries).\n\n"


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
    gavs: Dict[str, Dict] = dict()
    for pom in pom_paths:
        (g, a, v) = __parse_gav(pom, root)
        avs = gavs.get(g, dict())
        vers = avs.get(a, list())
        vers.append(v)
        avs[a] = vers
        gavs[g] = avs
    return gavs


def gen_meta_file(group_id, artifact_id: str, versions: list, root="/", digest=True) -> List[str]:
    content = MavenMetadata(
        group_id, artifact_id, versions
    ).generate_meta_file_content()
    g_path = "/".join(group_id.split("."))
    meta_files = []
    final_meta_path = os.path.join(root, g_path, artifact_id, MAVEN_METADATA_FILE)
    try:
        overwrite_file(final_meta_path, content)
        meta_files.append(final_meta_path)
    except FileNotFoundError as e:
        raise e
    if digest:
        meta_files.extend(__gen_all_digest_files(final_meta_path))
    return meta_files


def __gen_all_digest_files(meta_file_path: str) -> List[str]:
    md5_path = meta_file_path + ".md5"
    sha1_path = meta_file_path + ".sha1"
    sha256_path = meta_file_path + ".sha256"
    digest_files = []
    if __gen_digest_file(md5_path, meta_file_path, HashType.MD5):
        digest_files.append(md5_path)
    if __gen_digest_file(sha1_path, meta_file_path, HashType.SHA1):
        digest_files.append(sha1_path)
    if __gen_digest_file(sha256_path, meta_file_path, HashType.SHA256):
        digest_files.append(sha256_path)
    return digest_files


def __gen_digest_file(hash_file_path, meta_file_path: str, hashtype: HashType) -> bool:
    try:
        overwrite_file(hash_file_path, digest(meta_file_path, hashtype))
    except FileNotFoundError:
        logger.warning(
            "Error: Can not create digest file %s for %s "
            "because of some missing folders",
            hash_file_path, meta_file_path
        )
        return False
    return True


def handle_maven_uploading(
    repos: Union[str, List[str]],
    prod_key: str,
    ignore_patterns=None,
    root="maven-repository",
    targets: List[TARGET_TYPE] = None,
    aws_profile=None,
    dir_=None,
    do_index=True,
    gen_sign=False,
    cf_enable=False,
    key=None,
    dry_run=False,
    manifest_bucket_name=None,
    config=None
) -> Tuple[str, bool]:
    """ Handle the maven product release tarball uploading process.
        * repo is the location of the tarball in filesystem
        * prod_key is used to identify which product this repo
          tar belongs to
        * ignore_patterns is used to filter out paths which don't
          need to upload in the tarball
        * root is a prefix in the tarball to identify which path is
          the beginning of the maven GAV path
        * targets contains the target name with its bucket name and prefix
          for the bucket, which will be used to store artifacts with the
          prefix. See target definition in Charon configuration for details
        * dir_ is base dir for extracting the tarball, will use system
          tmp dir if None.

        Returns the directory used for archive processing and if the uploading is successful
    """
    if targets is None:
        targets = []
    if isinstance(repos, str):
        repos = [repos]
    # 1. extract tarballs
    tmp_root = _extract_tarballs(repos, root, prod_key, dir__=dir_)

    # 2. scan for paths and filter out the ignored paths,
    # and also collect poms for later metadata generation
    (top_level,
     valid_mvn_paths,
     valid_poms,
     valid_dirs) = _scan_paths(tmp_root, ignore_patterns, root)

    # This prefix is a subdir under top-level directory in tarball
    # or root before real GAV dir structure
    if not os.path.isdir(top_level):
        logger.error("Error: the extracted top-level path %s does not exist.", top_level)
        sys.exit(1)

    # 3. do validation for the files, like product version checking
    logger.info("Validating paths with rules.")
    (err_msgs, passed) = _validate_maven(valid_mvn_paths)
    if not passed:
        _handle_error(err_msgs)
        # Question: should we exit here?

    # 4. Do uploading
    s3_client = S3Client(aws_profile=aws_profile, dry_run=dry_run)
    targets_ = [(target[1], remove_prefix(target[2], "/")) for target in targets]
    logger.info(
        "Start uploading files to s3 buckets: %s",
        [target[1] for target in targets]
    )
    failed_files = s3_client.upload_files(
        file_paths=valid_mvn_paths,
        targets=targets_,
        product=prod_key,
        root=top_level
    )
    logger.info("Files uploading done\n")
    succeeded = True
    generated_signs = []
    for bucket in targets:
        # prepare cf invalidate files
        cf_invalidate_paths = []

        # 5. Do manifest uploading
        if not manifest_bucket_name:
            logger.warning(
                'Warning: No manifest bucket is provided, will ignore the process of manifest '
                'uploading\n')
        else:
            logger.info("Start uploading manifest to s3 bucket %s", manifest_bucket_name)
            manifest_folder = bucket[1]
            manifest_name, manifest_full_path = write_manifest(valid_mvn_paths, top_level, prod_key)
            s3_client.upload_manifest(
                manifest_name, manifest_full_path,
                manifest_folder, manifest_bucket_name
            )
            logger.info("Manifest uploading is done\n")

        # 6. Use uploaded poms to scan s3 for metadata refreshment
        bucket_name = bucket[1]
        prefix = remove_prefix(bucket[2], "/")
        logger.info("Start generating maven-metadata.xml files for bucket %s", bucket_name)
        meta_files = _generate_metadatas(
            s3=s3_client, bucket=bucket_name,
            poms=valid_poms, root=top_level,
            prefix=prefix
        )
        logger.info("maven-metadata.xml files generation done\n")
        failed_metas = meta_files.get(META_FILE_FAILED, [])

        # 7. Upload all maven-metadata.xml
        if META_FILE_GEN_KEY in meta_files:
            logger.info("Start updating maven-metadata.xml to s3 bucket %s", bucket_name)
            _failed_metas = s3_client.upload_metadatas(
                meta_file_paths=meta_files[META_FILE_GEN_KEY],
                target=(bucket_name, prefix),
                product=None,
                root=top_level
            )
            failed_metas.extend(_failed_metas)
            logger.info("maven-metadata.xml updating done in bucket %s\n", bucket_name)
            # Add maven-metadata.xml to CF invalidate paths
            if cf_enable:
                cf_invalidate_paths.extend(meta_files.get(META_FILE_GEN_KEY, []))

        # 8. Determine refreshment of archetype-catalog.xml
        if os.path.exists(os.path.join(top_level, MAVEN_ARCH_FILE)):
            logger.info("Start generating archetype-catalog.xml for bucket %s", bucket_name)
            upload_archetype_file = _generate_upload_archetype_catalog(
                s3=s3_client, bucket=bucket_name,
                root=top_level,
                prefix=prefix
            )
            logger.info("archetype-catalog.xml files generation done in bucket %s\n", bucket_name)

            # 9. Upload archetype-catalog.xml if it has changed
            if upload_archetype_file:
                archetype_files = [os.path.join(top_level, ARCHETYPE_CATALOG_FILENAME)]
                archetype_files.extend(
                    __hash_decorate_metadata(top_level, ARCHETYPE_CATALOG_FILENAME)
                )
                logger.info("Start updating archetype-catalog.xml to s3 bucket %s", bucket_name)
                _failed_metas = s3_client.upload_metadatas(
                    meta_file_paths=archetype_files,
                    target=(bucket_name, prefix),
                    product=None,
                    root=top_level
                )
                failed_metas.extend(_failed_metas)
                logger.info("archetype-catalog.xml updating done in bucket %s\n", bucket_name)
                # Add archtype-catalog to invalidate paths
                if cf_enable:
                    cf_invalidate_paths.extend(archetype_files)

        # 10. Generate signature file if contain_signature is set to True
        if gen_sign:
            conf = get_config(config)
            if not conf:
                sys.exit(1)
            suffix_list = __get_suffix(PACKAGE_TYPE_MAVEN, conf)
            command = conf.get_detach_signature_command()
            artifacts = [s for s in valid_mvn_paths if not s.endswith(tuple(suffix_list))]
            logger.info("Start generating signature for s3 bucket %s\n", bucket_name)
            (_failed_metas, _generated_signs) = signature.generate_sign(
                PACKAGE_TYPE_MAVEN, artifacts,
                top_level, prefix,
                s3_client, bucket_name,
                key, command
            )
            failed_metas.extend(_failed_metas)
            generated_signs.extend(_generated_signs)
            logger.info("Singature generation done.\n")

            logger.info("Start upload singature files to s3 bucket %s\n", bucket_name)
            _failed_metas = s3_client.upload_signatures(
                meta_file_paths=generated_signs,
                target=(bucket_name, prefix),
                product=None,
                root=top_level
            )
            failed_metas.extend(_failed_metas)
            logger.info("Signature uploading done.\n")

        # this step generates index.html for each dir and add them to file list
        # index is similar to metadata, it will be overwritten everytime
        if do_index:
            logger.info("Start generating index files to s3 bucket %s", bucket_name)
            created_indexes = indexing.generate_indexes(
                PACKAGE_TYPE_MAVEN,
                top_level, valid_dirs,
                s3_client, bucket_name, prefix
            )
            logger.info("Index files generation done.\n")

            logger.info("Start updating index files to s3 bucket %s", bucket_name)
            _failed_metas = s3_client.upload_metadatas(
                meta_file_paths=created_indexes,
                target=(bucket_name, prefix),
                product=None,
                root=top_level
            )
            failed_metas.extend(_failed_metas)
            logger.info("Index files updating done\n")
            # We will not invalidate the index files per cost consideration
            # if cf_enable:
            #     cf_invalidate_paths.extend(created_indexes)
        else:
            logger.info("Bypass indexing")

        # 11. Finally do the CF invalidating for metadata files
        if cf_enable and len(cf_invalidate_paths) > 0:
            cf_client = CFClient(aws_profile=aws_profile)
            cf_invalidate_paths = __wildcard_metadata_paths(cf_invalidate_paths)
            invalidate_cf_paths(cf_client, bucket, cf_invalidate_paths, top_level)

        upload_post_process(failed_files, failed_metas, prod_key, bucket_name)
        succeeded = succeeded and len(failed_files) <= 0 and len(failed_metas) <= 0

    return (tmp_root, succeeded)


def handle_maven_del(
    repo: str,
    prod_key: str,
    ignore_patterns=None,
    root="maven-repository",
    targets: List[TARGET_TYPE] = None,
    aws_profile=None,
    dir_=None,
    do_index=True,
    cf_enable=False,
    dry_run=False,
    manifest_bucket_name=None
) -> Tuple[str, bool]:
    """ Handle the maven product release tarball deletion process.
        * repo is the location of the tarball in filesystem
        * prod_key is used to identify which product this repo
          tar belongs to
        * ignore_patterns is used to filter out paths which don't
          need to upload in the tarball
        * root is a prefix in the tarball to identify which path is
          the beginning of the maven GAV path
        * targets contains the target name with its bucket name and prefix
          for the bucket, which will be used to store artifacts with the
          prefix. See target definition in Charon configuration for details
        * dir is base dir for extracting the tarball, will use system
          tmp dir if None.

        Returns the directory used for archive processing and if the rollback is successful
    """
    if targets is None:
        targets = []

    # 1. extract tarball
    tmp_root = _extract_tarball(repo, prod_key, dir__=dir_)

    # 2. scan for paths and filter out the ignored paths,
    # and also collect poms for later metadata generation
    (top_level,
     valid_mvn_paths,
     valid_poms,
     valid_dirs) = _scan_paths(tmp_root, ignore_patterns, root)

    # 3. Delete all valid_paths from s3
    logger.debug("Valid poms: %s", valid_poms)
    succeeded = True
    for target in targets:
        # prepare cf invalidation paths
        cf_invalidate_paths = []

        prefix = remove_prefix(target[2], "/")
        s3_client = S3Client(aws_profile=aws_profile, dry_run=dry_run)
        bucket_name = target[1]
        logger.info("Start deleting files from s3 bucket %s", bucket_name)
        failed_files = s3_client.delete_files(
            valid_mvn_paths,
            target=(bucket_name, prefix),
            product=prod_key,
            root=top_level
        )
        logger.info("Files deletion done\n")

        # 4. Delete related manifest from s3
        manifest_folder = target[1]
        logger.info(
            "Start deleting manifest from s3 bucket %s in folder %s",
            manifest_bucket_name, manifest_folder
        )
        s3_client.delete_manifest(prod_key, manifest_folder, manifest_bucket_name)
        logger.info("Manifest deletion is done\n")

        # 5. Use changed GA to scan s3 for metadata refreshment
        logger.info(
            "Start generating maven-metadata.xml files for all changed GAs in s3 bucket %s",
            bucket_name
        )
        meta_files = _generate_metadatas(
            s3=s3_client, bucket=bucket_name,
            poms=valid_poms, root=top_level,
            prefix=prefix
        )

        logger.info("maven-metadata.xml files generation done\n")

        # 6. Upload all maven-metadata.xml. We need to delete metadata files
        # firstly for all affected GA, and then replace the theirs content.
        logger.info("Start updating maven-metadata.xml to s3 bucket %s", bucket_name)
        all_meta_files = []
        for _, files in meta_files.items():
            all_meta_files.extend(files)
        s3_client.delete_files(
            file_paths=all_meta_files,
            target=(bucket_name, prefix),
            product=None,
            root=top_level
        )
        failed_metas = meta_files.get(META_FILE_FAILED, [])
        if META_FILE_GEN_KEY in meta_files:
            _failed_metas = s3_client.upload_metadatas(
                meta_file_paths=meta_files[META_FILE_GEN_KEY],
                target=(bucket_name, prefix),
                product=None,
                root=top_level
            )
            if len(_failed_metas) > 0:
                failed_metas.extend(_failed_metas)
        logger.info("maven-metadata.xml updating done\n")
        if cf_enable:
            logger.debug(
                "Extending invalidate_paths with %s:", all_meta_files
            )
            cf_invalidate_paths.extend(all_meta_files)

        # 7. Determine refreshment of archetype-catalog.xml
        if os.path.exists(os.path.join(top_level, MAVEN_ARCH_FILE)):
            logger.info("Start generating archetype-catalog.xml")
            archetype_action = _generate_rollback_archetype_catalog(
                s3=s3_client, bucket=bucket_name,
                root=top_level,
                prefix=prefix
            )
            logger.info("archetype-catalog.xml files generation done\n")

            # 8. Upload or Delete archetype-catalog.xml if it has changed
            archetype_files = [os.path.join(top_level, ARCHETYPE_CATALOG_FILENAME)]
            archetype_files.extend(__hash_decorate_metadata(top_level, ARCHETYPE_CATALOG_FILENAME))
            if archetype_action < 0:
                logger.info("Start updating archetype-catalog.xml to s3 bucket %s", bucket_name)
                _failed_metas = s3_client.delete_files(
                    file_paths=archetype_files,
                    target=(bucket_name, prefix),
                    product=None,
                    root=top_level
                )
                if len(_failed_metas) > 0:
                    failed_metas.extend(_failed_metas)
            elif archetype_action > 0:
                _failed_metas = s3_client.upload_metadatas(
                    meta_file_paths=archetype_files,
                    target=(bucket_name, prefix),
                    product=None,
                    root=top_level
                )
                if len(_failed_metas) > 0:
                    failed_metas.extend(_failed_metas)
            logger.info("archetype-catalog.xml updating done\n")
            if cf_enable:
                cf_invalidate_paths.extend(archetype_files)

        if do_index:
            logger.info("Start generating index files for all changed entries")
            created_indexes = indexing.generate_indexes(
                PACKAGE_TYPE_MAVEN, top_level, valid_dirs, s3_client, bucket_name, prefix
            )
            logger.info("Index files generation done.\n")

            logger.info("Start updating index to s3 bucket %s", bucket_name)
            _failed_index_files = s3_client.upload_metadatas(
                meta_file_paths=created_indexes,
                target=(bucket_name, prefix),
                product=None,
                root=top_level
            )
            if len(_failed_index_files) > 0:
                failed_metas.extend(_failed_index_files)
            logger.info("Index files updating done.\n")
            # We will not invalidate the index files per cost consideration
            # if cf_enable:
            #     cf_invalidate_paths.extend(created_indexes)
        else:
            logger.info("Bypassing indexing")

        # 9. Finally do the CF invalidating for metadata files
        if cf_enable and len(cf_invalidate_paths):
            cf_client = CFClient(aws_profile=aws_profile)
            cf_invalidate_paths = __wildcard_metadata_paths(cf_invalidate_paths)
            invalidate_cf_paths(cf_client, target, cf_invalidate_paths, top_level)

        rollback_post_process(failed_files, failed_metas, prod_key, bucket_name)
        succeeded = succeeded and len(failed_files) == 0 and len(failed_metas) == 0

    return (tmp_root, succeeded)


def _extract_tarball(repo: str, prefix="", dir__=None) -> str:
    if os.path.exists(repo):
        try:
            logger.info("Extracting tarball %s", repo)
            repo_zip = ZipFile(repo)
            tmp_root = mkdtemp(prefix=f"charon-{prefix}-", dir=dir__)
            extract_zip_all(repo_zip, tmp_root)
            return tmp_root
        except BadZipFile as e:
            logger.error("Tarball extraction error: %s", e)
            sys.exit(1)
    logger.error("Error: archive %s does not exist", repo)
    sys.exit(1)


def _extract_tarballs(repos: List[str], root: str, prefix="", dir__=None) -> str:
    """ Extract multiple zip archives to a temporary directory.
        * repos are the list of repo paths to extract
        * root is a prefix in the tarball to identify which path is
          the beginning of the maven GAV path
        * prefix is the prefix for temporary directory name
        * dir__ is the directory where temporary directories will be created.

        Returns the path to the merged temporary directory containing all extracted files
    """
    # Create final merge directory
    final_tmp_root = mkdtemp(prefix=f"charon-{prefix}-final-", dir=dir__)

    total_copied = 0
    total_overwritten = 0
    total_processed = 0

    # Collect all extracted directories first
    extracted_dirs = []

    for repo in repos:
        if os.path.exists(repo):
            try:
                logger.info("Extracting tarball %s", repo)
                repo_zip = ZipFile(repo)
                tmp_root = mkdtemp(prefix=f"charon-{prefix}-", dir=dir__)
                extract_zip_all(repo_zip, tmp_root)
                extracted_dirs.append(tmp_root)

            except BadZipFile as e:
                logger.error("Tarball extraction error: %s", e)
                sys.exit(1)
        else:
            logger.error("Error: archive %s does not exist", repo)
            sys.exit(1)

    # Merge all extracted directories
    if extracted_dirs:
        # Get top-level directory names for merged from all repos
        top_level_merged_name_dirs = []
        for extracted_dir in extracted_dirs:
            for item in os.listdir(extracted_dir):
                item_path = os.path.join(extracted_dir, item)
                # Check the root maven-repository subdirectory existence
                maven_repo_path = os.path.join(item_path, root)
                if os.path.isdir(item_path) and os.path.exists(maven_repo_path):
                    top_level_merged_name_dirs.append(item)
                    break

        # Create merged directory name
        merged_dir_name = (
            "_".join(top_level_merged_name_dirs) if top_level_merged_name_dirs else "merged"
        )
        merged_dest_dir = os.path.join(final_tmp_root, merged_dir_name)

        # Merge content from all extracted directories
        for extracted_dir in extracted_dirs:
            copied, overwritten, processed = _merge_directories_with_rename(
                extracted_dir, merged_dest_dir, root
            )
            total_copied += copied
            total_overwritten += overwritten
            total_processed += processed

            # Clean up temporary extraction directory
            rmtree(extracted_dir)

    logger.info(
        "All zips merged! Total copied: %s, Total overwritten: %s, Total processed: %s",
        total_copied,
        total_overwritten,
        total_processed,
    )
    return final_tmp_root


def _merge_directories_with_rename(src_dir: str, dest_dir: str, root: str):
    """ Recursively copy files from src_dir to dest_dir, overwriting existing files.
        * src_dir is the source directory to copy from
        * dest_dir is the destination directory to copy to.

        Returns Tuple of (copied_count, overwritten_count, processed_count)
    """
    copied_count = 0
    overwritten_count = 0
    processed_count = 0

    # Find the actual content directory
    content_root = src_dir
    for item in os.listdir(src_dir):
        item_path = os.path.join(src_dir, item)
        # Check the root maven-repository subdirectory existence
        maven_repo_path = os.path.join(item_path, root)
        if os.path.isdir(item_path) and os.path.exists(maven_repo_path):
            content_root = item_path
            break

    # pylint: disable=unused-variable
    for root_dir, dirs, files in os.walk(content_root):
        # Calculate relative path from content root
        rel_path = os.path.relpath(root_dir, content_root)
        dest_root = os.path.join(dest_dir, rel_path) if rel_path != '.' else dest_dir

        # Create destination directory if it doesn't exist
        os.makedirs(dest_root, exist_ok=True)

        # Copy all files, overwriting existing ones
        for file in files:
            src_file = os.path.join(root_dir, file)
            dest_file = os.path.join(dest_root, file)
            if os.path.exists(dest_file):
                overwritten_count += 1
                logger.debug("Overwritten: %s -> %s", src_file, dest_file)
            else:
                copied_count += 1
                logger.debug("Copied: %s -> %s", src_file, dest_file)

            processed_count += 1
            copy2(src_file, dest_file)

    logger.info(
        "One zip merged! Files copied: %s, Files overwritten: %s, Total files processed: %s",
        copied_count,
        overwritten_count,
        processed_count,
    )
    return copied_count, overwritten_count, processed_count


def _scan_paths(files_root: str, ignore_patterns: List[str],
                root: str) -> Tuple[str, List[str], List[str], List[str]]:
    # 2. scan for paths and filter out the ignored paths,
    # and also collect poms for later metadata generation
    logger.info("Scan %s to collect files", files_root)
    top_level = root
    valid_mvn_paths, non_mvn_paths, ignored_paths, valid_poms, valid_dirs = [], [], [], [], []
    changed_dirs = set()
    top_found = False
    for root_dir, dirs, names in os.walk(files_root):
        for directory in dirs:
            changed_dirs.add(os.path.join(root_dir, directory))
            if not top_found:
                if directory == top_level:
                    top_level = os.path.join(root_dir, directory)
                    top_found = True
                if os.path.join(root_dir, directory) == os.path.join(files_root, top_level):
                    top_level = os.path.join(files_root, top_level)
                    top_found = True

        for name in names:
            path = os.path.join(root_dir, name)
            if top_level in root_dir:
                # Let's wait to do the regex / pom examination until we
                # know we're inside a valid root directory.
                if _is_ignored(name, ignore_patterns):
                    ignored_paths.append(path)
                    continue

                valid_mvn_paths.append(path)

                if name.strip().endswith(".pom"):
                    valid_poms.append(path)
            else:
                non_mvn_paths.append(path)

    if len(non_mvn_paths) > 0:
        non_mvn_items = [n.replace(files_root, "") for n in non_mvn_paths]
        logger.info("These files are not in the specified "
                    "root dir %s, so will be ignored: \n%s",
                    root, non_mvn_items)
    if not top_found or top_level.strip() == "" or top_level.strip() == "/":
        logger.warning(
            "Warning: the root path %s does not exist in tarball,"
            " will use empty trailing prefix for the uploading",
            top_level
        )
        top_level = files_root
    else:
        for c in changed_dirs:
            if c.startswith(top_level):
                valid_dirs.append(c)
    logger.info("Files scanning done.\n")

    if ignore_patterns and len(ignore_patterns) > 0:
        logger.info(
            "Ignored paths with ignore_patterns %s as below:\n%s\n",
            ignore_patterns, "\n".join(ignored_paths)
        )

    return (top_level, valid_mvn_paths, valid_poms, valid_dirs)


def _generate_rollback_archetype_catalog(
    s3: S3Client, bucket: str,
    root: str, prefix: str = None
) -> int:
    """Determine whether the local archive contains /archetype-catalog.xml
       in the repo contents.
       If so, determine whether the archetype-catalog.xml is already
       available in the bucket. Merge (or unmerge) these catalogs and
       return an integer, indicating whether the bucket file should be
       replaced (+1), deleted (-1), or, in the case where no action is
       required, it will return NO-OP (0).

       NOTE: There are three return values:
         - +1 - UPLOAD the local catalog with its rolled back changes
         - -1 - DELETE the (now empty) bucket catalog
         - 0  - take no action
    """
    if prefix:
        remote = os.path.join(prefix, ARCHETYPE_CATALOG_FILENAME)
    else:
        remote = ARCHETYPE_CATALOG_FILENAME
    local = os.path.join(root, ARCHETYPE_CATALOG_FILENAME)
    # As the local archetype will be overwrittern later, we must keep
    # a cache of the original local for multi-targets support
    local_bak = os.path.join(root, ARCHETYPE_CATALOG_FILENAME + ".charon.bak")
    if os.path.exists(local) and not os.path.exists(local_bak):
        with open(local, "rb") as f:
            with open(local_bak, "w+", encoding="utf-8") as fl:
                fl.write(str(f.read(), encoding="utf-8"))

    # If there is no local catalog, this is a NO-OP
    if os.path.exists(local_bak):
        existed = False
        try:
            existed = s3.file_exists_in_bucket(bucket, remote)
        except ValueError as e:
            logger.error(
                "Error: Can not generate archtype-catalog.xml due to: %s", e
            )
            return 0
        if not existed:
            # If there is no catalog in the bucket...this is a NO-OP
            return 0
        else:
            # If there IS a catalog in the bucket, we need to merge or un-merge it.
            with open(local_bak, "rb") as f:
                try:
                    local_archetypes = _parse_archetypes(f.read())
                except ElementTree.ParseError:
                    logger.warning(
                        "Failed to parse archetype-catalog.xml from local archive with root: %s. "
                        "SKIPPING invalid archetype processing.",
                        root
                    )
                    return 0

            if len(local_archetypes) < 1:
                # If there are no local archetypes in the catalog,
                # there's nothing to do.
                logger.warning(
                    "No archetypes found in local archetype-catalog.xml, "
                    "even though the file exists! Skipping."
                )
                return 0

            else:
                # Read the archetypes from the bucket so we can do a merge / un-merge
                remote_xml = s3.read_file_content(bucket, remote)
                try:
                    remote_archetypes = _parse_archetypes(remote_xml)
                except ElementTree.ParseError:
                    logger.warning(
                        "Failed to parse archetype-catalog.xml from bucket: %s. "
                        "CLEANING invalid remote archetype-catalog.xml",
                        bucket
                    )
                    return -1

                if len(remote_archetypes) < 1:
                    # Nothing in the bucket. Clear out this empty file.
                    __gen_all_digest_files(local)
                    return -1

                else:
                    # If we're deleting, un-merge the local archetypes from
                    # the remote ones.
                    #
                    # NOTE: The ONLY reason we can get away with this kind of
                    # naive un-merge is that products only bother to publish
                    # archetypes for their own direct users. If they publish
                    # an archetype, it's only for use with their product.
                    # Therefore, if we rollback that product, the archetypes
                    # they reference shouldn't be useful anymore.
                    for la in local_archetypes:
                        if la in remote_archetypes:
                            remote_archetypes.remove(la)

                    if len(remote_archetypes) < 1:
                        # If there are no remote archetypes left after removing
                        # ours DELETE the bucket catalog.
                        __gen_all_digest_files(local)
                        return -1
                    else:
                        # Re-render the result of our archetype un-merge to the
                        # local file, in preparation for upload.
                        with open(local, 'wb') as f:
                            content = MavenArchetypeCatalog(remote_archetypes)\
                                .generate_meta_file_content()
                            try:
                                overwrite_file(local, content)
                            except FileNotFoundError as e:
                                logger.error(
                                    "Error: Can not create file %s because of some missing folders",
                                    local,
                                )
                                raise e
                        __gen_all_digest_files(local)
                        return 1

    return 0


def _generate_upload_archetype_catalog(
        s3: S3Client, bucket: str,
        root: str, prefix: str = None
) -> bool:
    """Determine whether the local archive contains /archetype-catalog.xml
       in the repo contents.
       If so, determine whether the archetype-catalog.xml is already
       available in the bucket. Merge (or unmerge) these catalogs and
       return a boolean indicating whether the local file should be uploaded.
    """
    remote = ARCHETYPE_CATALOG_FILENAME
    if prefix:
        remote = os.path.join(prefix, ARCHETYPE_CATALOG_FILENAME)
    local = os.path.join(root, ARCHETYPE_CATALOG_FILENAME)
    # As the local archetype will be overwrittern later, we must keep
    # a cache of the original local for multi-targets support
    local_bak = os.path.join(root, ARCHETYPE_CATALOG_FILENAME + ".charon.bak")
    if os.path.exists(local) and not os.path.exists(local_bak):
        with open(local, "rb") as f:
            with open(local_bak, "w+", encoding="utf-8") as fl:
                fl.write(str(f.read(), encoding="utf-8"))

    # If there is no local catalog, this is a NO-OP
    if os.path.exists(local_bak):
        existed = False
        try:
            existed = s3.file_exists_in_bucket(bucket, remote)
        except ValueError as e:
            logger.error(
                "Error: Can not generate archtype-catalog.xml due to: %s", e
            )
            return False
        if not existed:
            __gen_all_digest_files(local)
            # If there is no catalog in the bucket, just upload what we have locally
            return True
        else:
            # If there IS a catalog in the bucket, we need to merge or un-merge it.
            with open(local, "rb") as f:
                try:
                    local_archetypes = _parse_archetypes(f.read())
                except ElementTree.ParseError:
                    logger.warning(
                        "Failed to parse archetype-catalog.xml from local archive with root: %s. "
                        "SKIPPING invalid archetype processing.",
                        root
                    )
                    return False

            if len(local_archetypes) < 1:
                logger.warning(
                    "No archetypes found in local archetype-catalog.xml, "
                    "even though the file exists! Skipping."
                )

            else:
                # Read the archetypes from the bucket so we can do a merge / un-merge
                remote_xml = s3.read_file_content(bucket, remote)
                try:
                    remote_archetypes = _parse_archetypes(remote_xml)
                except ElementTree.ParseError:
                    logger.warning(
                        "Failed to parse archetype-catalog.xml from bucket: %s. "
                        "OVERWRITING bucket archetype-catalog.xml with the valid, local copy.",
                        bucket
                    )
                    return True

                if len(remote_archetypes) < 1:
                    __gen_all_digest_files(local)
                    # Nothing in the bucket. Just push what we have locally.
                    return True
                else:
                    original_remote_size = len(remote_archetypes)
                    for la in local_archetypes:
                        # The cautious approach in this operation contradicts
                        # assumptions we make for the rollback case.
                        # That's because we should NEVER encounter a collision
                        # on archetype GAV...they should belong with specific
                        # product releases.
                        #
                        # Still, we will WARN, not ERROR if we encounter this.
                        if la not in remote_archetypes:
                            remote_archetypes.append(la)
                        else:
                            logger.warning(
                                "\n\n\nDUPLICATE ARCHETYPE: %s. "
                                "This makes rollback of the current release UNSAFE!\n\n\n",
                                la
                            )

                    if len(remote_archetypes) != original_remote_size:
                        # If the number of archetypes in the version of
                        # the file from the bucket has changed, we need
                        # to regenerate the file and re-upload it.
                        #
                        # Re-render the result of our archetype merge /
                        # un-merge to the local file, in preparation for
                        # upload.
                        with open(local, 'wb') as f:
                            content = MavenArchetypeCatalog(remote_archetypes)\
                                .generate_meta_file_content()
                            try:
                                overwrite_file(local, content)
                            except FileNotFoundError as e:
                                logger.error(
                                    "Error: Can not create file %s because of some missing folders",
                                    local,
                                )
                                raise e
                        __gen_all_digest_files(local)
                        return True

    return False


def _parse_archetypes(source) -> List[ArchetypeRef]:
    tree = ElementTree.fromstring(
        source.strip(), forbid_dtd=True,
        forbid_entities=True, forbid_external=True
    )

    archetypes = []
    for a in tree.findall("./archetypes/archetype"):
        gid = a.find('groupId').text
        aid = a.find('artifactId').text
        ver = a.find('version').text
        desc = a.find('description').text
        archetypes.append(ArchetypeRef(gid, aid, ver, desc))

    return archetypes


def _generate_metadatas(
    s3: S3Client, bucket: str,
    poms: List[str], root: str,
    prefix: str = None
) -> Dict[str, List[str]]:
    """Collect GAVs and generating maven-metadata.xml.
       As all valid poms has been stored in s3 bucket,
       what we should do here is:
       * Scan and get the GA for the poms
       * Search all poms in s3 based on the GA
       * Use searched pomsto generate maven-metadata
         to refresh
    """
    ga_dict: Dict[str, bool] = {}
    logger.debug("Valid poms: %s", poms)
    valid_gavs_dict = parse_gavs(poms, root)
    for g, avs in valid_gavs_dict.items():
        for a in avs.keys():
            logger.debug("G: %s, A: %s", g, a)
            g_path = "/".join(g.split("."))
            ga_dict[os.path.join(g_path, a)] = True
    # Note: here we don't need to add original poms, because
    # they have already been uploaded to s3.
    all_poms: List[str] = []
    meta_files: Dict[str, List[str]] = {}
    for path, _ in ga_dict.items():
        # avoid some wrong prefix, like searching org/apache
        # but got org/apache-commons
        ga_prefix = path
        if prefix:
            ga_prefix = os.path.join(prefix, path)
        if not path.endswith("/"):
            ga_prefix = ga_prefix + "/"
        (existed_poms, success) = s3.get_files(bucket, ga_prefix, ".pom")
        if len(existed_poms) == 0:
            if success:
                logger.debug(
                    "No poms found in s3 bucket %s for GA path %s", bucket, path
                )
                meta_files_deletion = meta_files.get(META_FILE_DEL_KEY, [])
                meta_files_deletion.append(os.path.join(path, MAVEN_METADATA_FILE))
                meta_files_deletion.extend(__hash_decorate_metadata(path, MAVEN_METADATA_FILE))
                meta_files[META_FILE_DEL_KEY] = meta_files_deletion
            else:
                logger.warning("An error happened when scanning remote "
                               "artifacts under GA path %s", path)
                meta_failed_path = meta_files.get(META_FILE_FAILED, [])
                meta_failed_path.append(os.path.join(path, MAVEN_METADATA_FILE))
                meta_failed_path.extend(__hash_decorate_metadata(path, MAVEN_METADATA_FILE))
                meta_files[META_FILE_FAILED] = meta_failed_path
        else:
            logger.debug(
                "Got poms in s3 bucket %s for GA path %s: %s", bucket, path, poms
            )
            un_prefixed_poms = existed_poms
            if prefix:
                if not prefix.endswith("/"):
                    un_prefixed_poms = [remove_prefix(pom, prefix) for pom in existed_poms]
                else:
                    un_prefixed_poms = [remove_prefix(pom, prefix + "/") for pom in existed_poms]
            all_poms.extend(un_prefixed_poms)
    gav_dict = parse_gavs(all_poms)
    if len(gav_dict) > 0:
        meta_files_generation = []
        for g, avs in gav_dict.items():
            for a, vers in avs.items():
                try:
                    metas = gen_meta_file(g, a, vers, root)
                except FileNotFoundError:
                    logger.warning("Failed to create or update metadata file for GA"
                                   " %s, please check if aligned Maven GA"
                                   " is correct in your tarball.", f'{g}:{a}')
                logger.debug("Generated metadata file %s for %s:%s", meta_files, g, a)
                meta_files_generation.extend(metas)
        meta_files[META_FILE_GEN_KEY] = meta_files_generation
    return meta_files


def __hash_decorate_metadata(path: str, metadata: str) -> List[str]:
    return [
        os.path.join(path, metadata + hash) for hash in [".md5", ".sha1", ".sha256"]
    ]


def _is_ignored(filename: str, ignore_patterns: List[str]) -> bool:
    for ignored_name in STANDARD_GENERATED_IGNORES:
        if filename and filename.startswith(ignored_name.strip()):
            logger.info("Ignoring standard generated Maven path: %s", filename)
            return True

    if ignore_patterns:
        for dirs in ignore_patterns:
            if re.match(dirs, filename):
                return True
    return False


def _validate_maven(paths: List[str]) -> Tuple[List[str], bool]:
    # Reminder: need to implement later
    return (list(), True)


def _handle_error(err_msgs: List[str]):
    # Reminder: will implement later
    pass


def __get_suffix(package_type: str, conf: CharonConfig) -> List[str]:
    if package_type:
        suffix = conf.get_ignore_signature_suffix(package_type)
        if suffix:
            return suffix
    return []


def __wildcard_metadata_paths(paths: List[str]) -> List[str]:
    new_paths = []
    for path in paths:
        if path.endswith(MAVEN_METADATA_FILE)\
           or path.endswith(MAVEN_ARCH_FILE):
            new_paths.append(path[:-len(".xml")] + ".*")
        elif path.endswith(".md5")\
            or path.endswith(".sha1")\
            or path.endswith(".sha128")\
                or path.endswith(".sha256"):
            continue
        else:
            new_paths.append(path)
    return new_paths


class VersionCompareKey:
    'Used as key function for version sorting'
    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        return self.__compare(other) < 0

    def __gt__(self, other):
        return self.__compare(other) > 0

    def __le__(self, other):
        return self.__compare(other) <= 0

    def __ge__(self, other):
        return self.__compare(other) >= 0

    def __eq__(self, other):
        return self.__compare(other) == 0

    def __hash__(self) -> int:
        return self.obj.__hash__()

    def __compare(self, other) -> int:
        xitems = self.obj.split(".")
        if "-" in xitems[-1]:
            xitems = xitems[:-1] + xitems[-1].split("-")
        yitems = other.obj.split(".")
        if "-" in yitems[-1]:
            yitems = yitems[:-1] + yitems[-1].split("-")
        big = max(len(xitems), len(yitems))
        for i in range(big):
            try:
                xitem = xitems[i]
            except IndexError:
                return -1
            try:
                yitem = yitems[i]
            except IndexError:
                return 1
            if xitem.isnumeric() and yitem.isnumeric():
                xitem = int(xitem)
                yitem = int(yitem)
            elif xitem.isnumeric() and not yitem.isnumeric():
                return 1
            elif not xitem.isnumeric() and yitem.isnumeric():
                return -1
            if xitem > yitem:
                return 1
            elif xitem < yitem:
                return -1
            else:
                continue
        return 0


class ArchetypeCompareKey(VersionCompareKey):
    'Used as key function for GAV sorting'
    def __init__(self, gav):
        super().__init__(gav.version)
        self.gav = gav

    # pylint: disable=unused-private-member
    def __compare(self, other) -> int:
        x = self.gav.group_id + ":" + self.gav.artifact_id
        y = other.gav.group_id + ":" + other.gav.artifact_id

        if x == y:
            return 0
        elif x < y:
            return -1
        else:
            return 1
