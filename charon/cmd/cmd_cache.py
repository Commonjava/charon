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
from click import command, option, argument, group
from typing import List, Tuple

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
    The target to do the invalidating, which will decide the s3 bucket
    which and its related domain to get the distribution.
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
    The file which contain the paths to be invalidated in CF. Paths in this file follow the
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
def invalidate(
    target: str,
    paths: List[str],
    path_file: str,
    quiet: bool = False,
    debug: bool = False
):
    """Do invalidating on AWS CloudFront for the specified paths.
    """
    _decide_mode(
        f"cfclear-{target}", "",
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

    if path_file:
        with open(path_file, "r", encoding="utf-8") as f:
            for line in f.readlines():
                work_paths.append(str(line).strip())

    use_wildcard = False
    for path in work_paths:
        if "*" in path:
            use_wildcard = True
            break

    try:
        (buckets, aws_profile) = _init_cmd(target)

        for b in buckets:
            cf_client = CFClient(aws_profile=aws_profile)
            # Per aws official doc, if the paths contains wildcard, it is
            # limited to 15 as max items in one request. Otherwise it could
            # be 3000
            if use_wildcard:
                invalidate_cf_paths(
                    cf_client, b, work_paths
                )
            else:
                invalidate_cf_paths(
                    cf_client, b, work_paths, batch_size=3000
                )
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)


@argument(
    "invalidation_id",
    type=str
)
@option(
    "--target",
    "-t",
    "target",
    help="""
    The target to do the invalidating, which will decide the s3 bucket
    which and its related domain to get the distribution.
    """,
    required=True
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
def check(
    invalidation_id: str,
    target: str,
    quiet: bool = False,
    debug: bool = False
):
    """Check the invalidation status of the specified invalidation id
    for AWS CloudFront.
    """
    _decide_mode(
        f"cfcheck-{target}", "",
        is_quiet=quiet, is_debug=debug, use_log_file=False
    )
    try:
        (buckets, aws_profile) = _init_cmd(target)
        if not buckets:
            sys.exit(1)

        for b in buckets:
            cf_client = CFClient(aws_profile=aws_profile)
            bucket_name = b[1]
            domain = b[4]
            if not domain:
                domain = cf_client.get_domain_by_bucket(bucket_name)
            if domain:
                distr_id = cf_client.get_dist_id_by_domain(domain)
                if distr_id:
                    result = cf_client.check_invalidation(distr_id, invalidation_id)
                    logger.info(
                        "The status of invalidation %s is %s",
                        invalidation_id, result
                    )
            else:
                logger.error(
                    "Can not check invalidation result for %s because domain not found"
                    " for bucket %s. ", invalidation_id, bucket_name
                )
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)


def _init_cmd(target: str) -> Tuple[List[Tuple[str, str, str, str, str]], str]:
    conf = get_config()
    if not conf:
        sys.exit(1)

    aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
    if not aws_profile:
        logger.error("No AWS profile specified!")
        sys.exit(1)

    return (_get_buckets([target], conf), aws_profile)


@group()
def cf():
    """cf commands are responsible for the CloudFront cache operations in
    products operated by Charon
    """


def init_cf():
    cf.add_command(invalidate)
    cf.add_command(check)
