import mrrc.config as config
from tests.base import BaseMRRCTest


class ConfigTest(BaseMRRCTest):
    def test_config(self):
        conf = config.mrrc_config()
        self.assertEqual([".*^(redhat).*", ".*snapshot.*"], conf.get_ignore_patterns())
        self.assertEqual("FakeKey", conf.get_aws_key_id())
        self.assertEqual("FakePassword", conf.get_aws_key())
        aws_configs = conf.get_aws_configs()
        # self.assertEqual('https://s3.fake.com', aws_configs['endpoint_url'])
        self.assertEqual("us-east-1", aws_configs["region"])
        self.assertEqual("10", aws_configs["retry_max_attempts"])
        self.assertEqual("standard", aws_configs["retry_mode"])
