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
from charon.cmd.internal import _decide_mode
from charon.pkgs.indexing import re_index
from charon.constants import PACKAGE_TYPE_MAVEN, PACKAGE_TYPE_NPM
from click import command, option, argument

import traceback
import logging
import os
import sys

logger = logging.getLogger(__name__)


@argument(
    "path",
    type=str,
)
@option(
    "--target",
    "-t",
    help="""
    The target to do the index refreshing, which will decide
    which s3 bucket and what root path where all files will
    be deleted from.
    """,
    required=True
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
def index(
    path: str,
    target: str,
    debug: bool = False,
    quiet: bool = False,
    dryrun: bool = False
):
    """This command will re-generate the index.html files for the
    specified path.
    """
    _decide_mode(
        "index-{}".format(target), path.replace("/", "_"),
        is_quiet=quiet, is_debug=debug
    )
    try:
        conf = get_config()
        if not conf:
            sys.exit(1)

        aws_profile = os.getenv("AWS_PROFILE") or conf.get_aws_profile()
        if not aws_profile:
            logger.error("No AWS profile specified!")
            sys.exit(1)

        tgt = conf.get_target(target)
        if not tgt:
            # log is recorded get_target
            sys.exit(1)

        aws_bucket = None
        prefix = None
        for b in conf.get_target(target):
            aws_bucket = b.get('bucket')
            prefix = b.get('prefix', '')

        package_type = None
        if "maven" in aws_bucket:
            logger.info(
                "The target is a maven repository. Will refresh the index as maven package type"
            )
            package_type = PACKAGE_TYPE_MAVEN
        elif "npm" in aws_bucket:
            package_type = PACKAGE_TYPE_NPM
            logger.info(
                "The target is a npm repository. Will refresh the index as npm package type"
            )
        else:
            logger.error(
                "The target is not supported. Only maven or npm target is supported."
            )
            sys.exit(1)

        if not aws_bucket:
            logger.error("No bucket specified!")
            sys.exit(1)

        re_index(aws_bucket, prefix, path, package_type, aws_profile, dryrun)
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)  # distinguish between exception and bad config or bad state
