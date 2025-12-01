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
from typing import List

from charon.utils.archive import detect_npm_archives, NpmArchiveType
from charon.cmd.internal import _get_local_repos, _decide_mode
from charon.pkgs.maven import _extract_tarballs
from click import command, option, argument
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import mkdtemp

import logging
import os
import sys

logger = logging.getLogger(__name__)


@argument(
    "repos",
    type=str,
    nargs=-1  # This allows multiple arguments for zip urls
)
@option(
    "--product",
    "-p",
    help="""
    The product key, will combine with version to decide
    the metadata of the files in tarball.
    """,
    nargs=1,
    required=True,
    multiple=False,
)
@option(
    "--version",
    "-v",
    help="""
    The product version, will combine with key to decide
    the metadata of the files in tarball.
    """,
    required=True,
    multiple=False,
)
@option(
    "--root_path",
    "-r",
    default="maven-repository",
    help="""
    The root path in the tarball before the real maven paths,
    will be trailing off before uploading.
    """,
)
@option(
    "--work_dir",
    "-w",
    help="""
    The temporary working directory into which archives should
    be extracted, when needed.
    """,
)
@option(
    "--merge_result",
    "-m",
    help="""
    The path of the final merged zip file will be compressed and saved.
    Default is the ZIP file which is created in a temporary directory based on work_dir.
    e.g. /tmp/work/jboss-eap-8.1.0_merged_a1b2c3/jboss-eap-8.1.0_merged.zip
    """,
)
@option(
    "--debug",
    "-D",
    help="Debug mode, will print all debug logs for problem tracking.",
    is_flag=True,
    default=False
)
@option(
    "--quiet",
    "-q",
    help="Quiet mode, will shrink most of the logs except warning and errors.",
    is_flag=True,
    default=False
)
@command()
def merge(
        repos: List[str],
        product: str,
        version: str,
        root_path="maven-repository",
        work_dir=None,
        merge_result=None,
        debug=False,
        quiet=False
):
    """Merge multiple Maven ZIP archives and compress the result into a single ZIP file.
    The merged file is stored locally as specified by merge_result.

    Note: This function does not support merging single archive, NPM archives,
    or archives of inconsistent types.
    """
    _decide_mode(product, version, is_quiet=quiet, is_debug=debug)
    if len(repos) == 1:
        logger.info("Skip merge step, single archive detected, no merge needed")
        sys.exit(0)

    product_key = f"{product}-{version}"
    archive_paths = _get_local_repos(repos)
    archive_types = detect_npm_archives(archive_paths)

    maven_count = archive_types.count(NpmArchiveType.NOT_NPM)
    npm_count = len(archive_types) - maven_count
    if maven_count == len(archive_types):
        tmp_root = _extract_tarballs(archive_paths, root_path, product_key, dir__=work_dir)
        _create_merged_zip(tmp_root, merge_result, product_key, work_dir)
    elif npm_count == len(archive_types):
        logger.error("Skip merge step for the npm archives")
        sys.exit(1)
    else:
        logger.error("Skip merge step since the types are not consistent")
        sys.exit(1)


def _create_merged_zip(
        root_path: str,
        merge_result: str,
        product_key: str,
        work_dir: str
):
    zip_path = merge_result
    if not merge_result:
        merge_path = mkdtemp(prefix=f"{product_key}_merged_", dir=work_dir)
        zip_path = os.path.join(merge_path, f"{product_key}_merged.zip")

    # pylint: disable=unused-variable
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path to preserve directory structure
                arcname = os.path.relpath(file_path, root_path)
                zipf.write(file_path, arcname)
        logger.info("Done for the merged zip generation: %s", zip_path)
