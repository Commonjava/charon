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
from mrrc.utils.logs import set_logging, DEFAULT_LOGGER
import click
import logging

logger = logging.getLogger(DEFAULT_LOGGER)

@click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def init(debug=False):
    if debug:
        set_logging(level=logging.DEBUG)
    logger.info("upload not yet implemented!")


@click.argument('repo', type=click.Path(exists=True))
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration', nargs=1,
              required=True)
@click.option('--version', '-v', help='The product version, used in repository definition metadata', multiple=False)
@click.option('--ga', '-g', is_flag=True, default=False, multiple=False,
              help='Push content to the GA group (as opposed to earlyaccess)')
# @click.option('--type', '-t', default="maven", multiple=False,
#               help='The package type of the product archive, default is maven')
@click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def upload(repo: str, product: str, version: str, ga=False, debug=False):
    if debug:
        set_logging(level=logging.DEBUG)
    logger.info("upload not yet implemented!")

@click.argument('repo', type=click.Path(exists=True))
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration', nargs=1,
              required=True)
@click.option('--version', '-v', help='The product version, used in repository definition metadata', multiple=False)
@click.option('--ga', '-g', is_flag=True, default=False, multiple=False,
              help='Push content to the GA group (as opposed to earlyaccess)')
# @click.option('--type', '-t', is_flag=True, default="maven", multiple=False,
#               help='The package type of the product archive, default is maven')
@click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def delete(repo: str, product: str, version: str, ga=False, debug=False):
    if debug:
        set_logging(level=logging.DEBUG)
    logger.info("delete not yet implemented!")

@click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def gen(debug=False):
    if debug:
        set_logging(level=logging.DEBUG)
    logger.info("gen not yet implemented!")

@click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def ls(debug=False):
    if debug:
        set_logging(level=logging.DEBUG)
    logger.info("delete not yet implemented!")

@click.group()
def cli():
    pass