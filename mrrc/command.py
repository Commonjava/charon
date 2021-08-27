from mrrc.metadata_mvn import MavenMetadata
import click

@click.command()
def init():
  print("init not yet implemented!")

@click.command()
def upload():
  print("upload not yet implemented!")
  
@click.command()
def delete():
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