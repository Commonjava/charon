from configparser import ConfigParser, NoSectionError
from mrrc.utils.logs import DEFAULT_LOGGER 
import os
import sys
import logging

CONFIG_FILE = "mrrc-uploader.conf"

SECTION_AWS = 'aws'
SECTION_MRRC = 'mrrc'

AWS_KEY_ID = 'access_key_id'
AWS_KEY = 'secret_access_key'
AWS_ENDPOINT = 'endpoint_url'
AWS_REGION = 'region'
AWS_RETRY_MAX = 'retry_max_attempts'
AWS_RETRY_MODE = 'retry_mode'
AWS_BUCKET = "bucket"

AWS_DEFAULT_BUCKET="mrrc"

logger = logging.getLogger(DEFAULT_LOGGER)
class MrrcConfig(object):
    """ MrrcConfig is used to store all configurations for mrrc-uploader tools.
    The configuration file will be named as mrrc-uploader.conf, and will be stored 
    in $HOME/.mrrc/ folder by default.
    """
    def __init__(self, data: ConfigParser):
        self._aws_enabled = True
        try:
            self.__aws_configs = dict(data.items(SECTION_AWS))
        except NoSectionError:
            logging('Warning: Missing AWS section, aws related function can not work.')
            self._aws_enabled = False

        if self._aws_enabled:
            if AWS_KEY_ID not in self.__aws_configs:
                logging('Warning: Missing AWS access key id, aws related function can not work.')
                self._aws_enabled=False
            if AWS_KEY not in self.__aws_configs:
                logging('Warning: Missing AWS access secret key, aws related function can not work.')
                self._aws_enabled=False

    def get_aws_key_id(self) -> str:
        return self.__val_or_none(AWS_KEY_ID)
    
    def get_aws_key(self) -> str:
        return self.__val_or_none(AWS_KEY)
    
    def get_aws_region(self) -> str:
        return self.__val_or_none(AWS_REGION)

    def get_aws_configs(self) -> dict:
        return self.__aws_configs
    
    def get_aws_bucket(self) -> str:
        return self.__val_or_default(self.__aws_configs,AWS_BUCKET,AWS_DEFAULT_BUCKET)
    
    def is_aws_enabled(self) -> bool:
        return self._aws_enabled
    
    def __val_or_none(self, key: str):
        return self.__aws_configs[key] if self._aws_enabled and key in self.__aws_configs else None

def mrrc_config():
    parser = ConfigParser()
    config_file = os.path.join(os.environ['HOME'],'.mrrc', CONFIG_FILE)
    if not parser.read(config_file):
        logging(f'Error: not existed config file {config_file})')
        sys.exit(1)
    return MrrcConfig(parser)