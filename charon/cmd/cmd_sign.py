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

from charon.config import get_config, RadasConfig
from charon.cmd.internal import (
    _decide_mode, _safe_delete
)
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
    """
)
@option(
    "--result_path",
    "-p",
    help="""
    The path which will save the sign result file.
    """
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
    "--work_dir",
    "-w",
    help="""
    The temporary working directory into which archives should
    be extracted, when needed.
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
    """
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
    ignore_patterns: List[str] = None,
    work_dir: str = None,
    config: str = None,
    sign_key: str = "redhatdevel",
    debug=False,
    quiet=False,
    dryrun=False
):
    """Do signing against files in the repo zip in repo_url through
    radas service. The repo_url points to the maven zip repository
    in quay.io, which will be sent as the source of the signing.
    """
    tmp_dir = work_dir
    logger.debug("%s", ignore_patterns)
    try:
        current = datetime.datetime.now().strftime("%Y%m%d%I%M")
        _decide_mode("radas_sign", current, is_quiet=quiet, is_debug=debug)
        if dryrun:
            logger.info("Running in dry-run mode, no files will signed.")
        conf = get_config(config)
        if not conf:
            logger.error("The charon configuration is not valid!")
            sys.exit(1)
        radas_conf = conf.get_radas_config()
        if not radas_conf or not radas_conf.validate():
            logger.error("The configuration for radas is not valid!")
            sys.exit(1)
        sign_in_radas(repo_url, requester, sign_key, result_path, radas_conf)
    except Exception:
        print(traceback.format_exc())
        sys.exit(2)  # distinguish between exception and bad config or bad state
    finally:
        if not debug and tmp_dir:
            _safe_delete(tmp_dir)


def sign_in_radas(repo_url: str,
                  requester: str,
                  sign_key: str,
                  result_path: str,
                  radas_config: RadasConfig):
    '''This function will be responsible to do the overall controlling of the whole process,
    like trigger the send and register the receiver, and control the wait and timeout there.
    '''
    logger.debug("params. repo_url: %s, requester: %s, sign_key: %s, result_path: %s,"
                 "radas_config: %s", repo_url, requester, sign_key, result_path, radas_config)
    logger.info("Not implemented yet!")
