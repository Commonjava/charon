import configparser
import os
import sys

from mrrc.config import MrrcConfig

CONFIG_FILE = "mrrc-uploader.conf"

def test():
  parser = configparser.ConfigParser()
  config_file = os.path.join(os.environ['HOME'],'.mrrc', CONFIG_FILE)
  if not parser.read(config_file):
     sys.stderr.write(f'Error: not existed config file {config_file})')
     sys.exit(1)
  config = MrrcConfig(parser)
  print(config.get_aws_key_id())
  print(config.get_aws_key())
  print(config.get_aws_configs())

if __name__ == '__main__':
  test()
