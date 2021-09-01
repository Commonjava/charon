import mrrc.config as config
from tests.base import BaseMRRCTest
import configparser
import os
import sys

class ConfigTest(BaseMRRCTest):
    def test_config(self):
        parser = configparser.ConfigParser()
        config_file = os.path.join(os.environ['HOME'],'.mrrc', 'mrrc-uploader.conf')
        if not parser.read(config_file):
            self.fail(f'Error: not existed config file {config_file})')
        conf = config.MrrcConfig(parser)
        self.assertEqual('FakeKey', conf.get_aws_key_id())
        self.assertEqual('FakePassword', conf.get_aws_key())
        aws_configs = conf.get_aws_configs()
        self.assertEqual('https://s3.fake.com', aws_configs['endpoint_url'])
        self.assertEqual('us-east-1', aws_configs['region'])
        self.assertEqual('10', aws_configs['retry_max_attempts'])
        self.assertEqual('standard', aws_configs['retry_mode'])
        