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
from typing import List, Tuple

from charon.config import CharonConfig, get_config
from charon.constants import DEFAULT_REGISTRY
from charon.utils.logs import set_logging
from charon.utils.archive import detect_npm_archive, download_archive, NpmArchiveType
from charon.pkgs.maven import handle_maven_uploading, handle_maven_del
from charon.pkgs.npm import handle_npm_uploading, handle_npm_del
from click import command, option, argument, group
from json import loads
from shutil import rmtree

import traceback
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
    'targets',
    help="""
    The target to do the uploading, which will decide which s3 bucket
    and what root path where all files will be uploaded to.
    Can accept more than one target.
    """,
    required=True,
    multiple=True,
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
    "--work_dir",
    "-w",
    help="""
    The temporary working directory into which archives should
    be extracted, when needed.
    """,
)
@option(
    "--contain_signature",
    "-s",
    is_flag=True,
    help="""
    Toggle signature generation and upload feature in charon.
    """
)
@option(
    "--sign_key",
    "-k",
    help="""
    rpm-sign key to be used, will replace {{ key }} in default configuration for signature.
    Does noting if detach_signature_command does not contain {{ key }} field.
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
    targets: List[str],
    root_path="maven-repository",
    ignore_patterns: List[str] = None,
    work_dir: str = None,
    contain_signature: bool = False,
    sign_key: str = "redhatdevel",
    debug=False,
    quiet=False,
    dryrun=False
):
    """Upload all files from a released product REPO to Ronda
    Service. The REPO points to a product released tarball which
    is hosted in a remote url or a local path.
    """
    tmp_dir = work_dir
    try:
        __decide_mode(product, version, is_quiet=quiet, is_debug=debug)
        if dryrun:
            logger.info("Running in dry-run mode,"
                        "no files will be uploaded.")
        if not __validate_prod_key(product, version):
            return
        conf = get_config()
        if not conf:
            sys.exit(1)

        aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
        if not aws_profile:
            logger.error("No AWS profile specified!")
            sys.exit(1)

        archive_path = __get_local_repo(repo)
        npm_archive_type = detect_npm_archive(archive_path)
        product_key = f"{product}-{version}"
        manifest_bucket_name = conf.get_manifest_bucket()
        buckets = __get_buckets(targets, conf)
        if npm_archive_type != NpmArchiveType.NOT_NPM:
            logger.info("This is a npm archive")
            npm_root_path = root_path\
                if root_path and root_path != "maven-repository" else "package"
            tmp_dir, succeeded = handle_npm_uploading(
                archive_path,
                product_key,
                buckets=buckets,
                aws_profile=aws_profile,
                dir_=work_dir,
                root_path=npm_root_path,
                gen_sign=contain_signature,
                key=sign_key,
                dry_run=dryrun,
                manifest_bucket_name=manifest_bucket_name
            )
            if not succeeded:
                sys.exit(1)
        else:
            ignore_patterns_list = None
            if ignore_patterns:
                ignore_patterns_list = ignore_patterns
            else:
                ignore_patterns_list = __get_ignore_patterns(conf)
            logger.info("This is a maven archive")
            tmp_dir, succeeded = handle_maven_uploading(
                archive_path,
                product_key,
                ignore_patterns_list,
                root=root_path,
                buckets=buckets,
                aws_profile=aws_profile,
                dir_=work_dir,
                gen_sign=contain_signature,
                key=sign_key,
                dry_run=dryrun,
                manifest_bucket_name=manifest_bucket_name
            )
            if not succeeded:
                sys.exit(1)
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)  # distinguish between exception and bad config or bad state
    finally:
        if not debug:
            __safe_delete(tmp_dir)


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
    'targets',
    help="""
    The target to do the deletion, which will decide which s3 bucket
    and what root path where all files will be deleted from.
    Can accept more than one target.
    """,
    required=True,
    multiple=True,
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
    "--work_dir",
    "-w",
    help="""
    The temporary working directory into which archives should
    be extracted, when needed.
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
    targets: List[str],
    root_path="maven-repository",
    ignore_patterns: List[str] = None,
    work_dir: str = None,
    debug=False,
    quiet=False,
    dryrun=False
):
    """Roll back all files in a released product REPO from
    Ronda Service. The REPO points to a product released
    tarball which is hosted in a remote url or a local path.
    """
    tmp_dir = work_dir
    try:
        __decide_mode(product, version, is_quiet=quiet, is_debug=debug)
        if dryrun:
            logger.info("Running in dry-run mode,"
                        "no files will be deleted.")
        if not __validate_prod_key(product, version):
            return
        conf = get_config()
        if not conf:
            sys.exit(1)

        aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
        if not aws_profile:
            logger.error("No AWS profile specified!")
            sys.exit(1)

        archive_path = __get_local_repo(repo)
        npm_archive_type = detect_npm_archive(archive_path)
        product_key = f"{product}-{version}"
        manifest_bucket_name = conf.get_manifest_bucket()
        buckets = __get_buckets(targets, conf)
        if npm_archive_type != NpmArchiveType.NOT_NPM:
            logger.info("This is a npm archive")
            npm_root_path = root_path\
                if root_path and root_path != "maven-repository" else "package"
            tmp_dir, succeeded = handle_npm_del(
                archive_path,
                product_key,
                buckets=buckets,
                aws_profile=aws_profile,
                dir_=work_dir,
                root_path=npm_root_path,
                dry_run=dryrun,
                manifest_bucket_name=manifest_bucket_name
            )
            if not succeeded:
                sys.exit(1)
        else:
            ignore_patterns_list = None
            if ignore_patterns:
                ignore_patterns_list = ignore_patterns
            else:
                ignore_patterns_list = __get_ignore_patterns(conf)
            logger.info("This is a maven archive")
            tmp_dir, succeeded = handle_maven_del(
                archive_path,
                product_key,
                ignore_patterns_list,
                root=root_path,
                buckets=buckets,
                aws_profile=aws_profile,
                dir_=work_dir,
                dry_run=dryrun,
                manifest_bucket_name=manifest_bucket_name
            )
            if not succeeded:
                sys.exit(1)
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)  # distinguish between exception and bad config or bad state
    finally:
        if not debug:
            __safe_delete(tmp_dir)


def __get_buckets(targets: List[str], conf: CharonConfig) -> List[Tuple[str, str, str, str]]:
    buckets = []
    for target in targets:
        for bucket in conf.get_target(target):
            aws_bucket = bucket.get('bucket')
            prefix = bucket.get('prefix', '')
            registry = bucket.get('registry', DEFAULT_REGISTRY)
            buckets.append((target, aws_bucket, prefix, registry))
    return buckets


def __safe_delete(tmp_dir: str):
    if tmp_dir and os.path.exists(tmp_dir):
        logger.info("Cleaning up work directory: %s", tmp_dir)
        try:
            rmtree(tmp_dir)
        except Exception as e:
            logger.error("Failed to clear work directory. %s", e)


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


def __decide_mode(product: str, version: str, is_quiet: bool, is_debug: bool):
    if is_quiet:
        logger.info("Quiet mode enabled, "
                    "will only give warning and error logs.")
        set_logging(product, version, level=logging.WARNING)
    elif is_debug:
        logger.info("Debug mode enabled, "
                    "will give all debug logs for tracing.")
        set_logging(product, version, level=logging.DEBUG)
    else:
        set_logging(product, version, level=logging.INFO)


@group()
def cli():
    """Charon is a tool to synchronize several types of
       artifacts repository data to Red Hat Ronda
       service (maven.repository.redhat.com).
    """
