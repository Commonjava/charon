from mrrc.maven import MavenMetadata
from mrrc.npm import  NPMPackageMetadata
from mrrc.config import mrrc_config
import click

@click.command()
def init():
    print("init not yet implemented!")


@click.argument('repo', type=click.Path(exists=True))
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration', nargs=1,
              required=True)
@click.option('--version', '-v', help='The product version, used in repository definition metadata', multiple=False)
@click.option('--ga', '-g', is_flag=True, default=False, multiple=False,
              help='Push content to the GA group (as opposed to earlyaccess)')
# @click.option('--type', '-t', default="maven", multiple=False,
#               help='The package type of the product archive, default is maven')
# @click.option('--debug', '-D', is_flag=True, default=False)
@click.command()
def upload(repo: str, product: str, version: str, ga=False):
    print("upload not yet implemented!")

@click.argument('repo', type=click.Path(exists=True))
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration', nargs=1,
              required=True)
@click.option('--version', '-v', help='The product version, used in repository definition metadata', multiple=False)
@click.option('--ga', '-g', is_flag=True, default=False, multiple=False,
              help='Push content to the GA group (as opposed to earlyaccess)')
# @click.option('--type', '-t', is_flag=True, default="maven", multiple=False,
#               help='The package type of the product archive, default is maven')
@click.command()
def delete(repo: str, product: str, version: str, ga=False):
    print("delete not yet implemented!")

@click.command()
def gen():
    print("gen not yet implemented!")

@click.command()
def ls():
    print("ls not yet implemented!")

@click.group()
def cli():
    pass