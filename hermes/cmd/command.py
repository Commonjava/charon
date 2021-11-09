"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/hermes)

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
from hermes.config import get_config, AWS_DEFAULT_BUCKET
from hermes.utils.logs import set_logging
from hermes.utils.archive import detect_npm_archive, download_archive, NpmArchiveType
from hermes.pkgs.maven import handle_maven_uploading, handle_maven_del
from hermes.pkgs.npm import handle_npm_uploading, handle_npm_del
from click import command, option, argument, group
from json import loads

import logging
import os

logger = logging.getLogger(__name__)


@command()
def init():
    print("init not yet implemented!")


@argument("repo", type=str)
@option(
    "--product",
    "-p",
    help="The product key, used to lookup profileId from the configuration",
    nargs=1,
    required=True,
)
@option(
    "--version",
    "-v",
    help="The product version, used in repository definition metadata",
    multiple=False,
)
# @option(
#     "--ga",
#     "-g",
#     is_flag=True,
#     default=False,
#     multiple=False,
#     help="Push content to the GA group (as opposed to earlyaccess)",
# )
@option(
    "--bucket",
    "-b",
    help="""The name of S3 bucket which will be used to upload files.""",
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
    help="""The regex patterns list to filter out the paths which should
            not be allowed to upload to S3. Can accept more than one pattern
    """,
)
@option("--debug", "-D", is_flag=True, default=False)
@command()
def upload(
    repo: str,
    product: str,
    version: str,
    bucket,
    root_path="maven-repository",
    ignore_patterns=None,
    debug=False
):
    """Upload all files from a released product tarball to Mercury
    Service.
    """
    if debug:
        set_logging(level=logging.DEBUG)
    archive_path = __get_local_repo(repo)
    npm_archive_type = detect_npm_archive(archive_path)
    product_key = f"{product}-{version}"
    if npm_archive_type != NpmArchiveType.NOT_NPM:
        logger.info("This is a npm archive")
        handle_npm_uploading(archive_path, product_key,
                             bucket_name=__get_bucket(bucket))
    else:
        ignore_patterns_list = None
        if ignore_patterns:
            ignore_patterns_list = ignore_patterns
        else:
            ignore_patterns_list = __get_ignore_patterns()
        logger.info("This is a maven archive")
        handle_maven_uploading(archive_path, product_key,
                               ignore_patterns_list,
                               root=root_path,
                               bucket_name=__get_bucket(bucket))


@argument("repo", type=str)
@option(
    "--product",
    "-p",
    help="The product key, used to lookup profileId from the configuration",
    nargs=1,
    required=True,
)
@option(
    "--version",
    "-v",
    help="The product version, used in repository definition metadata",
    multiple=False,
)
# @option(
#     "--ga",
#     "-g",
#     is_flag=True,
#     default=False,
#     multiple=False,
#     help="Push content to the GA group (as opposed to earlyaccess)",
# )
@option(
    "--bucket",
    "-b",
    help="""The name of S3 bucket which will be used to delete files.""",
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
    help="""The regex patterns list to filter out the paths which should
            not be allowed to upload to S3. Can accept more than one pattern
    """,
)
@option("--debug", "-D", is_flag=True, default=False)
@command()
def delete(
    repo: str,
    product: str,
    version: str,
    bucket,
    root_path="maven-repository",
    ignore_patterns=None,
    debug=False
):
    """Roll back all files in a released product tarball from
    Mercury Service.
    """
    if debug:
        set_logging(level=logging.DEBUG)
    archive_path = __get_local_repo(repo)
    npm_archive_type = detect_npm_archive(archive_path)
    product_key = f"{product}-{version}"
    if npm_archive_type != NpmArchiveType.NOT_NPM:
        logger.info("This is a npm archive")
        handle_npm_del(archive_path, product_key,
                       bucket_name=__get_bucket(bucket))
    else:
        ignore_patterns_list = None
        if ignore_patterns:
            ignore_patterns_list = ignore_patterns
        else:
            ignore_patterns_list = __get_ignore_patterns()
        logger.info("This is a maven archive")
        handle_maven_del(archive_path, product_key,
                         ignore_patterns_list,
                         root=root_path,
                         bucket_name=__get_bucket(bucket))


def __get_ignore_patterns() -> List[str]:
    ignore_patterns = os.getenv("HERMES_IGNORE_PATTERNS")
    if ignore_patterns:
        try:
            return loads(ignore_patterns)
        except (ValueError, TypeError):
            logger.warning("Warning: ignore_patterns %s specified in "
                           "system environment, but not a valid json "
                           "style array. Will skip it.", ignore_patterns)
    conf = get_config()
    if conf:
        return conf.get_ignore_patterns()
    return None


def __get_bucket(param_bucket: str) -> str:
    if param_bucket and param_bucket != "":
        logger.info("AWS bucket '%s' is specified in option"
                    ", will use it for following process", param_bucket)
        return param_bucket
    TARGET_BUCKET = "HERMES_BUCKET"
    bucket = os.getenv(TARGET_BUCKET)
    if bucket:
        logger.info("AWS bucket '%s' found in system environment var '%s'"
                    ", will use it for following process", bucket, TARGET_BUCKET)
        return bucket
    conf = get_config()
    if conf:
        return conf.get_aws_bucket()
    return AWS_DEFAULT_BUCKET


def __get_local_repo(url: str) -> str:
    archive_path = url
    if url.startswith("http://") or url.startswith("https://"):
        logger.info("Start downloading tarball %s", url)
        archive_path = download_archive(url)
        logger.info("Tarball downloaded at: %s", archive_path)
    return archive_path


@group()
def cli():
    """Hermes is a tool to synchronize several types of
       artifacts repository data to Red Hat Mercury
       service (maven.repository.redhat.com).
    """
