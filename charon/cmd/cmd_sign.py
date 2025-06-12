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
from charon.pkgs.radas_sign import sign_in_radas
from charon.cmd.internal import _decide_mode
from charon.constants import DEFAULT_RADAS_SIGN_IGNORES

from click import command, option, argument

import traceback
import logging
import sys
import datetime

logger = logging.getLogger(__name__)


@argument(
    "repo_url",
    type=str
)
@option(
    "--requester",
    "-r",
    help="""
    The requester who sends the signing request.
    """,
    required=True
)
@option(
    "--result_path",
    "-p",
    help="""
    The path which will save the sign result file.
    """,
    required=True
)
@option(
    "--ignore_patterns",
    "-i",
    multiple=True,
    help="""
    The regex patterns list to filter out the files which should
    not be allowed to upload to S3. Can accept more than one pattern.
    """
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
    "--sign_key",
    "-k",
    help="""
    rpm-sign key to be used, will replace {{ key }} in default configuration for signature.
    Does noting if detach_signature_command does not contain {{ key }} field.
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
@command()
def sign(
    repo_url: str,
    requester: str,
    result_path: str,
    sign_key: str,
    ignore_patterns: List[str] = None,
    config: str = None,
    debug=False,
    quiet=False
):
    """Do signing against files in the repo zip in repo_url through
    radas service. The repo_url points to the maven zip repository
    in quay.io, which will be sent as the source of the signing.
    """
    logger.debug("%s", ignore_patterns)
    try:
        current = datetime.datetime.now().strftime("%Y%m%d%I%M")
        _decide_mode("radas_sign", current, is_quiet=quiet, is_debug=debug)
        conf = get_config(config)
        if not conf:
            logger.error("The charon configuration is not valid!")
            sys.exit(1)
        radas_conf = conf.get_radas_config()
        if not radas_conf or not radas_conf.validate():
            logger.error("The configuration for radas is not valid!")
            sys.exit(1)
        # All ignore files in global config should also be ignored in signing.
        ig_patterns = conf.get_ignore_patterns()
        ig_patterns.extend(DEFAULT_RADAS_SIGN_IGNORES)
        if ignore_patterns:
            ig_patterns.extend(ignore_patterns)
        ig_patterns = list(set(ig_patterns))
        args = {
            "repo_url": repo_url,
            "requester": requester,
            "sign_key": sign_key,
            "result_path": result_path,
            "ignore_patterns": ig_patterns,
            "radas_config": radas_conf
        }
        sign_in_radas(**args)  # type: ignore
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)
