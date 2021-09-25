import logging
from mrrc.logs import set_logging, DEFAULT_LOGGER
from mrrc.maven import MavenMetadata
from mrrc.npm import  NPMPackageMetadata
from mrrc.config import mrrc_config
import click

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
    logger.debug("This is a debug msg")
    logger.info("This is a info msg")
    logger.warning("This is a warn msg")
    logger.error("This is an error msg")

@click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def ls(debug=False):
    if debug:
        set_logging(level=logging.DEBUG)
    logger.info("delete not yet implemented!")

@click.group()
def cli():
    pass