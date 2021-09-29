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
from typing import List
from configparser import ConfigParser, NoSectionError
import os
import sys
import logging
import json

CONFIG_FILE = "mrrc-uploader.conf"

SECTION_MRRC = 'mrrc'
MRRC_IGNORE_PATTERN = "ignore_patterns"

SECTION_AWS = 'aws'
AWS_KEY_ID = 'access_key_id'
AWS_KEY = 'secret_access_key'
AWS_ENDPOINT = 'endpoint_url'
AWS_REGION = 'region'
AWS_RETRY_MAX = 'retry_max_attempts'
AWS_RETRY_MODE = 'retry_mode'
AWS_BUCKET = "bucket"
AWS_DEFAULT_BUCKET = "mrrc"


AWS_DEFAULT_BUCKET="mrrc"

logger = logging.getLogger(__name__)

class MrrcConfig(object):
    """ MrrcConfig is used to store all configurations for mrrc-uploader tools.
    The configuration file will be named as mrrc-uploader.conf, and will be stored 
    in $HOME/.mrrc/ folder by default.
    """
    def __init__(self, data: ConfigParser):
        try:
            self.__mrrc_configs = dict(data.items(SECTION_MRRC))
        except NoSectionError:
            pass
        
        self.__aws_enabled = True
        try:
            self.__aws_configs = dict(data.items(SECTION_AWS))
        except NoSectionError:
            logger.warning('Missing AWS section, aws related function can not work.')
            self.__aws_enabled = False

        if self.__aws_enabled:
            if AWS_KEY_ID not in self.__aws_configs:
                logger.warning('Missing AWS access key id, aws related function can not work.')
                self.__aws_enabled=False
            if AWS_KEY not in self.__aws_configs:
                logger.warning('Missing AWS access secret key, aws related function can not work.')
                self.__aws_enabled=False

    def get_aws_key_id(self) -> str:
        return self.__val_or_default(self.__aws_configs,AWS_KEY_ID)
    
    def get_aws_key(self) -> str:
        return self.__val_or_default(self.__aws_configs,AWS_KEY)
    
    def get_aws_region(self) -> str:
        return self.__val_or_default(self.__aws_configs,AWS_REGION)

    def get_aws_configs(self) -> dict:
        return self.__aws_configs
    
    def get_aws_bucket(self) -> str:
        return self.__val_or_default(self.__aws_configs,AWS_BUCKET,AWS_DEFAULT_BUCKET)
    
    def is_aws_enabled(self) -> bool:
        return self.__aws_enabled
    
    def get_ignore_patterns(self) -> List[str]:
        pattern_str = self.__val_or_default(self.__mrrc_configs, MRRC_IGNORE_PATTERN)
        if pattern_str and pattern_str.strip()!="":
            return json.loads(pattern_str)
        else:
            return None
    
    def __val_or_default(self, section:dict, key: str, default=None):
        return section[key] if section and key in section else default

def mrrc_config():
    parser = ConfigParser()
    config_file = os.path.join(os.environ['HOME'],'.mrrc', CONFIG_FILE)
    if not parser.read(config_file):
        logger.error(f'Config file {config_file} doesn\'t exist')
        sys.exit(1)
    return MrrcConfig(parser)