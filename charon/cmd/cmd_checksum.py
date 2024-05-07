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

from charon.config import get_config
from charon.pkgs.checksum_http import (
    handle_checksum_validation_http, refresh_checksum
)
from charon.cmd.internal import _decide_mode
from click import command, option, argument, group

import traceback
import logging
import os
import sys

logger = logging.getLogger(__name__)


@argument(
    "path",
    type=str
)
@option(
    "--debug",
    "-D",
    "debug",
    help="Debug mode, will print all debug logs for problem tracking.",
    is_flag=True,
    default=False
)
@option(
    "--quiet",
    "-q",
    "quiet",
    help="Quiet mode, will shrink most of the logs except warning and errors.",
    is_flag=True,
    default=False
)
@option(
    "--skip",
    "-k",
    "skips",
    multiple=True,
    help="""
    Paths to be skipped. This is used for recursive mode when $PATH has sub folders.
    """
)
@option(
    "--recursive",
    "-r",
    "recursive",
    help="""
    Decide if do validation recursively in the specified path.
    Warning: if the path is high level which contains lots of sub path(e.g org/
    or com/), set this flag will take very long time to do the validation.
    """,
    is_flag=True,
    default=False
)
@option(
    "--report-file-path",
    "-f",
    "report_file_path",
    help="""
    The path where the final report files will be generated
    """
)
@option(
    "--includes",
    "-i",
    "includes",
    help="""
    The comma splitted file suffix for all files that need to
    validate. e.g, ".jar,.pom,.xml". If not specified, will use
    default file types
    """
)
@option(
    "--target",
    "-t",
    "target",
    help="""
    The target to do the uploading, which will decide which s3 bucket
    and what root path where all files will be uploaded to.
    Can accept more than one target.
    """,
    required=True
)
@command()
def validate(
    path: str,
    target: str,
    includes: List[str],
    report_file_path: str,
    skips: List[str],
    recursive: bool = False,
    quiet: bool = False,
    debug: bool = False
):
    """
    Validate the checksum of the specified path for themaven repository.
    It will calculate the sha1 checksum of all artifact files in the
    specified path and compare with the companied .sha1 files of the
    artifacts, then record all mismatched artifacts in the report file.
    If some artifact files misses the companied .sha1 files, they will also
    be recorded.
    """
    _decide_mode(
        "checksum-validate-{}".format(target), path.replace("/", "_"),
        is_quiet=quiet, is_debug=debug
    )
    try:
        (aws_bucket, prefix) = _init_cmd(target)

        # NOTE: This is a liitle hacky, which constrain the configuration of
        #       of target should define the bucket to contain "prod-maven"
        #       or "stage-maven" to decide that the bucket is for maven repo
        #       in our defined aws env for production or stage
        if "prod-maven" not in aws_bucket and "stage-maven" not in aws_bucket:
            logger.error("The target %s is not a maven repository.", target)
            sys.exit(1)

        root_path = os.path.join(prefix, path)
        skip_paths = [os.path.join(prefix, p) for p in skips if p != "" and p != "/"]
        if path == "/":
            root_path = prefix
        handle_checksum_validation_http(
            aws_bucket, root_path, includes, report_file_path, recursive, skip_paths
        )
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)


@option(
    "--debug",
    "-D",
    "debug",
    help="Debug mode, will print all debug logs for problem tracking.",
    is_flag=True,
    default=False
)
@option(
    "--quiet",
    "-q",
    "quiet",
    help="Quiet mode, will shrink most of the logs except warning and errors.",
    is_flag=True,
    default=False
)
@option(
    "--path",
    "-p",
    "paths",
    help="""
    The paths of artifact files to do checksum refreshing.
    """,
    multiple=True
)
@option(
    "--path-file",
    "-f",
    "path_file",
    help="""
    The file which contain the paths of artifact files to do checksum refreshing.
    Each path in this file should be in a single line.
    """
)
@option(
    "--target",
    "-t",
    "target",
    help="""
    The target to do the uploading, which will decide which s3 bucket
    and what root path where all files will be uploaded to.
    Can accept more than one target.
    """,
    required=True
)
@command()
def refresh(
    target: str,
    paths: List[str],
    path_file: str,
    quiet: bool = False,
    debug: bool = False
):
    """
    Refresh the checksum of the specified path for the target maven repository.
    It will calculate the checksum files of the specified artifact and see if
    unmatched, then regenerate the checksum files based on the artifact.
    Default checksum files include .md5, .sha1.
    """
    _decide_mode(
        "checksum-refresh-{}".format(target), "",
        is_quiet=quiet, is_debug=debug, use_log_file=False
    )
    if not paths and not path_file:
        logger.error(
            "No path specified, please specify at least one path "
            "through --path or --path-file.")
        sys.exit(1)

    work_paths = []
    if paths:
        work_paths.extend(paths)

    conf = get_config()
    aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
    if not aws_profile:
        logger.error("No AWS profile specified!")
        sys.exit(1)

    if path_file:
        with open(path_file, "r", encoding="utf-8") as f:
            for line in f.readlines():
                work_paths.append(str(line).strip())
    try:
        (aws_bucket, prefix) = _init_cmd(target)

        # NOTE: This is a liitle hacky, which constrain the configuration of
        #       of target should define the bucket to contain "prod-maven"
        #       or "stage-maven" to decide that the bucket is for maven repo
        #       in our defined aws env for production or stage
        if "prod-maven" not in aws_bucket and "stage-maven" not in aws_bucket:
            logger.error("The target %s is not a maven repository.", target)
            sys.exit(1)

        refresh_checksum((aws_bucket, prefix), work_paths, aws_profile)
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)


def _init_cmd(target: str) -> Tuple[str, str]:
    conf = get_config()
    if not conf:
        sys.exit(1)
    aws_bucket = ""
    t = conf.get_target(target)
    if not t:
        sys.exit(1)
    for b in t:
        aws_bucket = b.get('bucket')
        prefix = b.get('prefix', '')
    return (aws_bucket, prefix)


@group()
def checksum():
    """checksum commands are responsible to operate checksum files
    of maven products operated by Charon
    """


def init_checksum():
    checksum.add_command(validate)
    checksum.add_command(refresh)
