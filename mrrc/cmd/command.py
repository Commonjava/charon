"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

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
from mrrc.utils.logs import set_logging
from mrrc.utils.archive import detect_npm_archive, NpmArchiveType
from mrrc.pkgs.maven import handle_maven_uploading, handle_maven_del
from click import command, option, argument, group, Path
from json import loads
import logging

logger = logging.getLogger(__name__)


@command()
def init():
    print("init not yet implemented!")


@argument("repo", type=Path(exists=True))
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
@option(
    "--ga",
    "-g",
    is_flag=True,
    default=False,
    multiple=False,
    help="Push content to the GA group (as opposed to earlyaccess)",
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
    default="",
    help="""The regex patterns list to filter out the paths which should
            not be allowed to upload to S3. Use json list to include more
            than one patterns (e.g, ["pattern1", "pattern2"])
    """,
)
@option("--debug", "-D", is_flag=True, default=False)
@command()
def upload(
    repo: str,
    product: str,
    version: str,
    ga=False,
    root_path="maven-repository",
    ignore_patterns="",
    debug=False
):
    if debug:
        set_logging(level=logging.DEBUG)
    npm_archive_type = detect_npm_archive(repo)
    product_key = f"{product}-{version}"
    if npm_archive_type != NpmArchiveType.NOT_NPM:
        # if any npm archive types....
        # Reminder: do npm repo handling here
        logger.info("This is a npm archive")
    else:
        ignore_patterns_list = []
        if ignore_patterns != "":
            ignore_patterns_list = loads(ignore_patterns)
        logger.info("This is a maven archive")
        handle_maven_uploading(repo, product_key, ga, ignore_patterns_list, root=root_path)


@argument("repo", type=Path(exists=True))
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
@option(
    "--ga",
    "-g",
    is_flag=True,
    default=False,
    multiple=False,
    help="Push content to the GA group (as opposed to earlyaccess)",
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
    default="",
    help="""The regex patterns list to filter out the paths which should
            not be allowed to upload to S3. Use json list to include more
            than one patterns (e.g, ["pattern1", "pattern2"])
    """,
)
@option("--debug", "-D", is_flag=True, default=False)
@command()
def delete(
    repo: str,
    product: str,
    version: str,
    ga=False,
    root_path="maven-repository",
    ignore_patterns="",
    debug=False
):
    if debug:
        set_logging(level=logging.DEBUG)
    npm_archive_type = detect_npm_archive(repo)
    product_key = f"{product}-{version}"
    if npm_archive_type != NpmArchiveType.NOT_NPM:
        # if any npm archive types....
        # Reminder: do npm repo handling here
        logger.info("This is a npm archive")
    else:
        logger.info("This is a maven archive")
        ignore_patterns_list = []
        if ignore_patterns != "":
            ignore_patterns_list = loads(ignore_patterns)
        handle_maven_del(repo, product_key, ga, ignore_patterns_list, root=root_path)


# @option('--debug', '-D', is_flag=True, default=False)
# @command()
# def gen(debug=False):
#     if debug:
#         set_logging(level=logging.DEBUG)
#     logger.info("gen not yet implemented!")

# @option('--debug', '-D', is_flag=True, default=False)
# @command()
# def ls(debug=False):
#     if debug:
#         set_logging(level=logging.DEBUG)
#     logger.info("ls not yet implemented!")


@group()
def cli():
    pass
