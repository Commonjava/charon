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

from charon.config import get_config
from charon.utils.archive import detect_npm_archives, NpmArchiveType
from charon.pkgs.maven import handle_maven_uploading
from charon.pkgs.npm import handle_npm_uploading
from charon.cmd.internal import (
    _decide_mode, _validate_prod_key,
    _get_local_repos, _get_targets,
    _get_ignore_patterns, _safe_delete
)
from click import command, option, argument

import traceback
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
    "--config",
    "-c",
    help="""
    The charon configuration yaml file path. Default is
    $HOME/.charon/charon.yaml
    """
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
    repos: List[str],
    product: str,
    version: str,
    targets: List[str],
    root_path="maven-repository",
    ignore_patterns: List[str] = None,
    work_dir: str = None,
    config: str = None,
    contain_signature: bool = False,
    sign_key: str = "redhatdevel",
    debug=False,
    quiet=False,
    dryrun=False
):
    """Upload all files from released product REPOs to Ronda
    Service. The REPOs point to a product released tarballs which
    are hosted in remote urls or local paths.
    """
    tmp_dir = work_dir
    try:
        _decide_mode(product, version, is_quiet=quiet, is_debug=debug)
        if dryrun:
            logger.info("Running in dry-run mode,"
                        "no files will be uploaded.")
        if not _validate_prod_key(product, version):
            return
        conf = get_config(config)
        if not conf:
            sys.exit(1)

        aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
        if not aws_profile:
            logger.error("No AWS profile specified!")
            sys.exit(1)

        archive_paths = _get_local_repos(repos)
        archive_types = detect_npm_archives(archive_paths)
        product_key = f"{product}-{version}"
        manifest_bucket_name = conf.get_manifest_bucket()
        targets_ = _get_targets(targets, conf)
        if not targets_:
            logger.error(
                "The targets %s can not be found! Please check"
                " your charon configuration to confirm the targets"
                " are set correctly.", targets_
            )
            sys.exit(1)

        maven_count = archive_types.count(NpmArchiveType.NOT_NPM)
        npm_count = len(archive_types) - maven_count
        if maven_count == len(archive_types):
            ignore_patterns_list = None
            if ignore_patterns:
                ignore_patterns_list = ignore_patterns
            else:
                ignore_patterns_list = _get_ignore_patterns(conf)
            logger.info("This is a maven archive")
            tmp_dir, succeeded = handle_maven_uploading(
                archive_paths,
                product_key,
                ignore_patterns_list,
                root=root_path,
                targets=targets_,
                aws_profile=aws_profile,
                dir_=work_dir,
                gen_sign=contain_signature,
                cf_enable=conf.is_aws_cf_enable(),
                key=sign_key,
                dry_run=dryrun,
                manifest_bucket_name=manifest_bucket_name,
                config=config
            )
            if not succeeded:
                sys.exit(1)
        elif npm_count == len(archive_types) and len(archive_types) == 1:
            logger.info("This is a npm archive")
            tmp_dir, succeeded = handle_npm_uploading(
                archive_paths[0],
                product_key,
                targets=targets_,
                aws_profile=aws_profile,
                dir_=work_dir,
                gen_sign=contain_signature,
                cf_enable=conf.is_aws_cf_enable(),
                key=sign_key,
                dry_run=dryrun,
                manifest_bucket_name=manifest_bucket_name
            )
            if not succeeded:
                sys.exit(1)
        elif npm_count == len(archive_types) and len(archive_types) > 1:
            logger.error("Doesn't support multiple upload for npm")
            sys.exit(1)
        else:
            logger.error("Upload types are not consistent")
            sys.exit(1)
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)  # distinguish between exception and bad config or bad state
    finally:
        if not debug and tmp_dir:
            _safe_delete(tmp_dir)
