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
from json import load, loads, dump, JSONDecodeError
import tarfile
from tempfile import mkdtemp
from typing import List, Set, Tuple

from semantic_version import compare

import charon.pkgs.indexing as indexing
import charon.pkgs.signature as signature
from charon.config import CharonConfig, get_config
from charon.constants import META_FILE_GEN_KEY, META_FILE_DEL_KEY, PACKAGE_TYPE_NPM
from charon.storage import S3Client
from charon.utils.archive import extract_npm_tarball
from charon.pkgs.pkg_utils import upload_post_process, rollback_post_process
from charon.utils.strings import remove_prefix
from charon.utils.files import write_manifest
from charon.utils.map import del_none

logger = logging.getLogger(__name__)

PACKAGE_JSON = "package.json"


class NPMPackageMetadata(object):
    """ This NPMPackageMetadata will represent the npm package(not version) package.json.
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
        tarball_path: str,
        product: str,
        buckets: List[Tuple[str, str, str, str]] = None,
        aws_profile=None,
        dir_=None,
        do_index=True,
        key_id=None,
        key_file=None,
        passphrase=None,
        dry_run=False,
        manifest_bucket_name=None
) -> Tuple[str, bool]:
    """ Handle the npm product release tarball uploading process.
        For NPM uploading, tgz file and version metadata will be relocated based
        on the native npm structure, package metadata will follow the base.
        * tarball_path is the location of the tarball in filesystem
        * product is used to identify which product this repo
          tar belongs to
        * buckets contains the target name with its bucket name and prefix
          for the bucket, which will be used to store artifacts with the
          prefix. See target definition in Charon configuration for details
        * dir_ is base dir for extracting the tarball, will use system
          tmp dir if None.

        Returns the directory used for archive processing and if uploading is successful
    """
    client = S3Client(aws_profile=aws_profile, dry_run=dry_run)
    generated_signs = []
    for bucket in buckets:
        bucket_name = bucket[1]
        prefix = remove_prefix(bucket[2], "/")
        registry = bucket[3]
        target_dir, valid_paths, package_metadata = _scan_metadata_paths_from_archive(
            tarball_path, registry, prod=product, dir__=dir_
        )
        if not os.path.isdir(target_dir):
            logger.error("Error: the extracted target_dir path %s does not exist.", target_dir)
            sys.exit(1)
        valid_dirs = __get_path_tree(valid_paths, target_dir)

        logger.info("Start uploading files to s3 buckets: %s", bucket_name)
        failed_files = client.upload_files(
            file_paths=[valid_paths[0]],
            targets=[(bucket_name, prefix)],
            product=product,
            root=target_dir
        )
        logger.info("Files uploading done\n")

        succeeded = True

        if not manifest_bucket_name:
            logger.warning(
                'Warning: No manifest bucket is provided, will ignore the process of manifest '
                'uploading\n')
        else:
            logger.info("Start uploading manifest to s3 bucket %s", manifest_bucket_name)
            manifest_folder = bucket_name
            manifest_name, manifest_full_path = write_manifest(valid_paths, target_dir, product)

            client.upload_manifest(
                manifest_name, manifest_full_path,
                manifest_folder, manifest_bucket_name
            )
            logger.info("Manifest uploading is done\n")

        logger.info(
            "Start generating version-level package.json for package: %s in s3 bucket %s",
            package_metadata.name, bucket_name
        )
        failed_metas = []
        _version_metadata_path = valid_paths[1]
        _failed_metas = client.upload_metadatas(
            meta_file_paths=[_version_metadata_path],
            target=(bucket_name, prefix),
            product=product,
            root=target_dir
        )
        failed_metas.extend(_failed_metas)
        logger.info("version-level package.json uploading done")

        logger.info(
            "Start generating package.json for package: %s in s3 bucket %s",
            package_metadata.name, bucket_name
        )
        meta_files = _gen_npm_package_metadata_for_upload(
            client, bucket_name, target_dir, package_metadata, prefix
        )
        logger.info("package.json generation done\n")

        if META_FILE_GEN_KEY in meta_files:
            _failed_metas = client.upload_metadatas(
                meta_file_paths=[meta_files[META_FILE_GEN_KEY]],
                target=(bucket_name, prefix),
                product=None,
                root=target_dir
            )
            failed_metas.extend(_failed_metas)
            logger.info("package.json uploading done")

        if (key_id is not None or key_file is not None) and passphrase is not None:
            conf = get_config()
            if not conf:
                sys.exit(1)
            suffix_list = __get_suffix(PACKAGE_TYPE_NPM, conf)
            artifacts = []
            for suffix in suffix_list:
                artifacts.extend([s for s in valid_paths if s.endswith(suffix)])
            if META_FILE_GEN_KEY in meta_files:
                artifacts.extend(meta_files[META_FILE_GEN_KEY])
            logger.info("Start generating signature for s3 bucket %s\n", bucket_name)
            (_failed_metas, _generated_signs) = signature.generate_sign(
                PACKAGE_TYPE_NPM, artifacts,
                target_dir, prefix,
                client, bucket_name,
                key_id, key_file, passphrase
            )
            failed_metas.extend(_failed_metas)
            generated_signs.extend(_generated_signs)
            logger.info("Singature generation done.\n")

            logger.info("Start upload singature files to s3 bucket %s\n", bucket_name)
            _failed_metas = client.upload_signatures(
                meta_file_paths=generated_signs,
                target=(bucket_name, prefix),
                product=None,
                root=target_dir
            )
            failed_metas.extend(_failed_metas)
            logger.info("Signature uploading done.\n")

        # this step generates index.html for each dir and add them to file list
        # index is similar to metadata, it will be overwritten everytime
        if do_index:
            logger.info("Start generating index files to s3 bucket %s", bucket_name)
            created_indexes = indexing.generate_indexes(
                PACKAGE_TYPE_NPM, target_dir, valid_dirs, client, bucket_name, prefix
            )
            logger.info("Index files generation done.\n")

            logger.info("Start updating index files to s3 bucket %s", bucket_name)
            _failed_metas = client.upload_metadatas(
                meta_file_paths=created_indexes,
                target=(bucket_name, prefix),
                product=None,
                root=target_dir
            )
            failed_metas.extend(_failed_metas)
            logger.info("Index files updating done\n")
        else:
            logger.info("Bypass indexing\n")

        upload_post_process(failed_files, failed_metas, product, bucket_name)
        succeeded = succeeded and len(failed_files) == 0 and len(failed_metas) == 0

    return (target_dir, succeeded)


def handle_npm_del(
        tarball_path: str,
        product: str,
        buckets: List[Tuple[str, str, str, str]] = None,
        aws_profile=None,
        dir_=None,
        do_index=True,
        dry_run=False,
        manifest_bucket_name=None
) -> Tuple[str, str]:
    """ Handle the npm product release tarball deletion process.
        * tarball_path is the location of the tarball in filesystem
        * product is used to identify which product this repo
          tar belongs to
        * buckets contains the target name with its bucket name and prefix
          for the bucket, which will be used to store artifacts with the
          prefix. See target definition in Charon configuration for details
        * dir is base dir for extracting the tarball, will use system
          tmp dir if None.

        Returns the directory used for archive processing and if the rollback is successful
    """
    target_dir, package_name_path, valid_paths = _scan_paths_from_archive(
        tarball_path, prod=product, dir__=dir_
    )

    valid_dirs = __get_path_tree(valid_paths, target_dir)

    client = S3Client(aws_profile=aws_profile, dry_run=dry_run)
    succeeded = True
    for bucket in buckets:
        bucket_name = bucket[1]
        prefix = remove_prefix(bucket[2], "/")
        logger.info("Start deleting files from s3 bucket %s", bucket_name)
        failed_files = client.delete_files(
            file_paths=valid_paths,
            target=(bucket_name, prefix),
            product=product, root=target_dir
        )
        logger.info("Files deletion done\n")

        if manifest_bucket_name:
            manifest_folder = bucket[1]
            logger.info(
                "Start deleting manifest from s3 bucket %s in folder %s",
                manifest_bucket_name, manifest_folder
            )
            client.delete_manifest(product, manifest_folder, manifest_bucket_name)
            logger.info("Manifest deletion is done\n")
        else:
            logger.warning(
                'Warning: No manifest bucket is provided, will ignore the process of manifest '
                'deletion\n')

        logger.info(
            "Start generating package.json for package: %s in bucket %s",
            package_name_path, bucket_name
        )
        meta_files = _gen_npm_package_metadata_for_del(
            client, bucket_name, target_dir, package_name_path, prefix
        )
        logger.info("package.json generation done\n")

        logger.info("Start uploading package.json to s3 bucket %s", bucket_name)
        all_meta_files = []
        for _, file in meta_files.items():
            all_meta_files.append(file)
        client.delete_files(
            file_paths=all_meta_files,
            target=(bucket_name, prefix),
            product=None, root=target_dir
        )
        failed_metas = []
        if META_FILE_GEN_KEY in meta_files:
            _failed_metas = client.upload_metadatas(
                meta_file_paths=[meta_files[META_FILE_GEN_KEY]],
                target=(bucket_name, prefix),
                product=None,
                root=target_dir
            )
            failed_metas.extend(_failed_metas)
        logger.info("package.json uploading done")

        if do_index:
            logger.info(
                "Start generating index files for all changed entries for bucket %s",
                bucket_name
            )
            created_indexes = indexing.generate_indexes(
                PACKAGE_TYPE_NPM, target_dir, valid_dirs, client, bucket_name, prefix
            )
            logger.info("Index files generation done.\n")

            logger.info("Start updating index to s3 bucket %s", bucket_name)
            _failed_index_files = client.upload_metadatas(
                meta_file_paths=created_indexes,
                target=(bucket_name, prefix),
                product=None,
                root=target_dir
            )
            failed_metas.extend(_failed_index_files)
            logger.info("Index files updating done.\n")
        else:
            logger.info("Bypassing indexing\n")

        rollback_post_process(failed_files, failed_metas, product, bucket_name)
        succeeded = succeeded and len(failed_files) <= 0 and len(failed_metas) <= 0

    return (target_dir, succeeded)


def read_package_metadata_from_content(content: str, is_version) -> NPMPackageMetadata:
    try:
        package_metadata = loads(content)
        return NPMPackageMetadata(package_metadata, is_version)
    except JSONDecodeError:
        logger.error('Error: Failed to parse json!')


def _gen_npm_package_metadata_for_upload(
        client: S3Client, bucket: str,
        target_dir: str, source_package: NPMPackageMetadata,
        prefix: str = None
) -> dict:
    """Collect NPM versions package.json and generate the package package.json.
       For uploading mode, package.json will merge the original in S3 with the local source.
       What we should do here is:
       * Scan the valid paths and source from the archive
       * Read from local source(uploading)
       * Use converted package.json to generate the package.json then update in S3
    """
    meta_files = {}
    package_metadata_key = os.path.join(source_package.name, PACKAGE_JSON)
    if prefix and prefix != "/":
        package_metadata_key = os.path.join(prefix, package_metadata_key)
    (package_json_files, success) = client.get_files(
        bucket_name=bucket,
        prefix=package_metadata_key
    )
    if not success:
        logger.warning("Error to get remote metadata files for %s", package_metadata_key)
    result = source_package
    if len(package_json_files) > 0:
        result = _merge_package_metadata(
            source_package, client, bucket, package_json_files[0]
        )
        logger.debug("Merge the S3 %s with local source", package_json_files[0])
    meta_file = _write_package_metadata_to_file(result, target_dir)
    meta_files[META_FILE_GEN_KEY] = meta_file
    return meta_files


def _gen_npm_package_metadata_for_del(
        client: S3Client, bucket: str,
        target_dir: str, package_path_prefix: str,
        prefix: str = None
) -> dict:
    """Collect NPM versions package.json and generate the package package.json.
       For del mode, all the version package.json contents to be merged will be read from S3.
       What we should do here is:
       * Scan the valid paths from the archive
       * Search the target contents in s3(del)
       * Use converted package.jsons to generate the package.json then update in S3
    """
    meta_files = {}
    package_metadata_key = os.path.join(package_path_prefix, PACKAGE_JSON)
    prefix_meta_key = package_metadata_key
    path_prefix = package_path_prefix
    if prefix and prefix != "/":
        prefix_meta_key = os.path.join(prefix, package_metadata_key)
        path_prefix = os.path.join(prefix, package_path_prefix)
    (existed_version_metas, success) = client.get_files(
        bucket_name=bucket, prefix=path_prefix, suffix=PACKAGE_JSON
    )
    if not success:
        logger.warning("Error to get remote metadata files "
                       "for %s when deletion", path_prefix)
    # ensure the metas only contain version package.json
    if prefix_meta_key in existed_version_metas:
        existed_version_metas.remove(prefix_meta_key)
    # Still have versions in S3 and need to maintain the package metadata
    if len(existed_version_metas) > 0:
        logger.debug("Read all version package.json content from S3")
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
        logger.debug("Final merged package metadata is %s", str(original.__dict__))
        meta_file = _write_package_metadata_to_file(original, target_dir)
        meta_files[META_FILE_GEN_KEY] = meta_file
    # Empty versions is S3 so don't need to maintain the package metadata
    else:
        meta_files[META_FILE_DEL_KEY] = package_metadata_key
    return meta_files


def _scan_metadata_paths_from_archive(path: str, registry: str, prod="", dir__=None) ->\
        Tuple[str, list, NPMPackageMetadata]:
    tmp_root = mkdtemp(prefix=f"npm-charon-{prod}-", dir=dir__)
    try:
        _, valid_paths = extract_npm_tarball(path, tmp_root, True, registry)
        if len(valid_paths) > 1:
            version = _scan_for_version(valid_paths[1])
            package = NPMPackageMetadata(version, True)
        return tmp_root, valid_paths, package
    except tarfile.TarError as e:
        logger.error("Tarball extraction error: %s", e)
        sys.exit(1)


def _scan_paths_from_archive(path: str, prod="", dir__=None) -> Tuple[str, str, list]:
    tmp_root = mkdtemp(prefix=f"npm-charon-{prod}-", dir=dir__)
    package_name_path, valid_paths = extract_npm_tarball(path, tmp_root, False)
    return tmp_root, package_name_path, valid_paths


def _merge_package_metadata(
        package_metadata: NPMPackageMetadata,
        client: S3Client, bucket: str,
        key: str
):
    content = client.read_file_content(bucket, key)
    original = read_package_metadata_from_content(content, False)

    if original:
        source_version = list(package_metadata.versions.keys())[0]
        is_latest = _is_latest_version(source_version, list(original.versions.keys()))
        _do_merge(original, package_metadata, is_latest)
        return original


def _scan_for_version(path: str):
    try:
        with open(path, encoding='utf-8') as version_meta_file:
            return load(version_meta_file)
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
            dump(del_none(package_metadata.__dict__.copy()), f)
        return final_package_metadata_path
    except FileNotFoundError:
        logger.error(
            'Can not create file %s because of some missing folders', final_package_metadata_path
        )


def __get_path_tree(paths: str, prefix: str) -> Set[str]:
    valid_dirs = set()
    for f in paths:
        dir_ = os.path.dirname(f)
        if dir_.startswith(prefix):
            dir_ = dir_[len(prefix):]
        if dir_.startswith("/"):
            dir_ = dir_[1:]
        if dir_.startswith("@"):
            valid_dirs.add(dir_.split("/")[0])
    return valid_dirs


def __get_suffix(package_type: str, conf: CharonConfig) -> List[str]:
    if package_type:
        return conf.get_artifact_suffix(package_type)
    return []
