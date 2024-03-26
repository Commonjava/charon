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

from charon.config import get_config
from charon.cmd.internal import _decide_mode, _get_buckets
from charon.cache import CFClient
from charon.pkgs.pkg_utils import invalidate_cf_paths
from click import command, option
from typing import List

import traceback
import logging
import sys
import os

logger = logging.getLogger(__name__)


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
@option(
    "--path",
    "-p",
    "paths",
    help="""
    The paths which will be invalidated in CF. The path can use the format as CF defining
    in https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html
    """,
    multiple=True
)
@option(
    "--path-file",
    "-f",
    "path_file",
    help="""
    The file which contain the paths to be invalidated in CF. Pahts in this file follow the
    format of CF defining too, and each path should be in a single line.
    """
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
@command()
def clear_cf(
    target: str,
    paths: List[str],
    path_file: str,
    quiet: bool = False,
    debug: bool = False
):
    """This command will do invalidating on AWS CloudFront for the specified paths.
    """
    _decide_mode(
        f"cfclear-{target}", "",
        is_quiet=quiet, is_debug=debug
    )
    if not paths and not path_file:
        logger.error(
            "No path specified, please specify at least one path "
            "through --path or --path-file.")
        sys.exit(1)

    work_paths = []
    if paths:
        work_paths.extend(paths)

    if path_file:
        with open(path_file, "r", encoding="utf-8") as f:
            for line in f.readlines():
                work_paths.append(str(line).strip())

    try:
        conf = get_config()
        if not conf:
            sys.exit(1)

        aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
        if not aws_profile:
            logger.error("No AWS profile specified!")
            sys.exit(1)

        buckets = _get_buckets([target], conf)

        for b in buckets:
            cf_client = CFClient(aws_profile=aws_profile)
            invalidate_cf_paths(
                cf_client, b, work_paths
            )
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)
