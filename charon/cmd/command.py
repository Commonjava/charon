"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
from charon.config import CharonConfig, get_config
from charon.utils.logs import set_logging
from charon.utils.archive import detect_npm_archive, download_archive, NpmArchiveType
from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from click import command, option, argument, group
from json import loads

import logging
import os
import sys

logger = logging.getLogger(__name__)


@argument(
    "repo",
    type=str,
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
    "--target",
    "-t",
    help="""
    The target to do the uploading, which will decide which s3 bucket
    and what root path where all files will be uploaded to.
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
    "--ignore_patterns",
    "-i",
    multiple=True,
    help="""
    The regex patterns list to filter out the files which should
    not be allowed to upload to S3. Can accept more than one pattern.
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
@option("--dryrun", "-n", is_flag=True, default=False)
@command()
def upload(
    repo: str,
    product: str,
    version: str,
    target: str,
    root_path="maven-repository",
    ignore_patterns=None,
    debug=False,
    quiet=False,
    dryrun=False
):
    """Upload all files from a released product REPO to Ronda
    Service. The REPO points to a product released tarball which
    is hosted in a remote url or a local path.
    """
    if dryrun:
        logger.info("Running in dry-run mode,"
                    "no files will be uploaded.")
    __decide_mode(is_quiet=quiet, is_debug=debug)
    if not __validate_prod_key(product, version):
        return
    conf = get_config()
    if not conf:
        sys.exit(1)
    aws_bucket = conf.get_aws_bucket(target)
    if not aws_bucket:
        sys.exit(1)
    archive_path = __get_local_repo(repo)
    npm_archive_type = detect_npm_archive(archive_path)
    product_key = f"{product}-{version}"
    if npm_archive_type != NpmArchiveType.NOT_NPM:
        logger.info("This is a npm archive")
        handle_npm_uploading(archive_path, product_key,
                             bucket_name=aws_bucket,
                             dry_run=dryrun)
    else:
        ignore_patterns_list = None
        if ignore_patterns:
            ignore_patterns_list = ignore_patterns
        else:
            ignore_patterns_list = __get_ignore_patterns(conf)
        logger.info("This is a maven archive")
        handle_maven_uploading(archive_path, product_key,
                               ignore_patterns_list,
                               root=root_path,
                               bucket_name=aws_bucket,
                               dry_run=dryrun)


@argument(
    "repo",
    type=str,
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
        The product version, will combine with product to decide
        the metadata of the files in tarball.
    """,
    required=True,
    multiple=False,
)
@option(
    "--target",
    "-t",
    help="""
    The target to do the deletion, which will decide which s3 bucket
    and what root path where all files will be deleted from.
    """,
    required=True,
    multiple=False,
)
@option(
    "--root_path",
    "-r",
    default="maven-repository",
    help="""The root path in the tarball before the real maven paths,
            will be trailing off before uploading
    """,
)
@option(
    "--ignore_patterns",
    "-i",
    multiple=True,
    help="""
    The regex patterns list to filter out the files which should
    not be allowed to upload to S3. Can accept more than one pattern.
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
@option("--dryrun", "-n", is_flag=True, default=False)
@command()
def delete(
    repo: str,
    product: str,
    version: str,
    target: str,
    root_path="maven-repository",
    ignore_patterns=None,
    debug=False,
    quiet=False,
    dryrun=False
):
    """Roll back all files in a released product REPO from
    Ronda Service. The REPO points to a product released
    tarball which is hosted in a remote url or a local path.
    """
    if dryrun:
        logger.info("Running in dry-run mode,"
                    "no files will be deleted.")
    __decide_mode(is_quiet=quiet, is_debug=debug)
    if not __validate_prod_key(product, version):
        return
    conf = get_config()
    if not conf:
        sys.exit(1)
    aws_bucket = conf.get_aws_bucket(target)
    if not aws_bucket:
        sys.exit(1)
    archive_path = __get_local_repo(repo)
    npm_archive_type = detect_npm_archive(archive_path)
    product_key = f"{product}-{version}"
    if npm_archive_type != NpmArchiveType.NOT_NPM:
        logger.info("This is a npm archive")
        handle_npm_del(archive_path, product_key,
                       bucket_name=aws_bucket,
                       dry_run=dryrun)
    else:
        ignore_patterns_list = None
        if ignore_patterns:
            ignore_patterns_list = ignore_patterns
        else:
            ignore_patterns_list = __get_ignore_patterns(conf)
        logger.info("This is a maven archive")
        handle_maven_del(archive_path, product_key,
                         ignore_patterns_list,
                         root=root_path,
                         bucket_name=aws_bucket,
                         dry_run=dryrun)


def __get_ignore_patterns(conf: CharonConfig) -> List[str]:
    ignore_patterns = os.getenv("CHARON_IGNORE_PATTERNS")
    if ignore_patterns:
        try:
            return loads(ignore_patterns)
        except (ValueError, TypeError):
            logger.warning("Warning: ignore_patterns %s specified in "
                           "system environment, but not a valid json "
                           "style array. Will skip it.", ignore_patterns)
    if conf:
        return conf.get_ignore_patterns()
    return None


def __get_local_repo(url: str) -> str:
    archive_path = url
    if url.startswith("http://") or url.startswith("https://"):
        logger.info("Start downloading tarball %s", url)
        archive_path = download_archive(url)
        logger.info("Tarball downloaded at: %s", archive_path)
    return archive_path


def __validate_prod_key(product: str, version: str) -> bool:
    if not product or product.strip() == "":
        logger.error("Error: product can not be empty!")
        return False
    if not version or version.strip() == "":
        logger.error("Error: version can not be empty!")
        return False
    if "," in product:
        logger.error("Error: there are invalid characters in product!")
        return False
    if "," in version:
        logger.error("Error: there are invalid characters in version!")
        return False
    return True


def __decide_mode(is_quiet: bool, is_debug: bool):
    if is_quiet:
        logger.info("Quiet mode enabled, "
                    "will only give warning and error logs.")
        set_logging(level=logging.WARNING)
    elif is_debug:
        logger.info("Debug mode enabled, "
                    "will give all debug logs for tracing.")
        set_logging(level=logging.DEBUG)


@group()
def cli():
    """Charon is a tool to synchronize several types of
       artifacts repository data to Red Hat Ronda
       service (maven.repository.redhat.com).
    """
