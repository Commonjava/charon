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

SECTION_MRRC = "mrrc"
MRRC_IGNORE_PATTERN = "ignore_patterns"

AWS_BUCKET = "bucket"
AWS_DEFAULT_BUCKET = "mrrc"


logger = logging.getLogger(__name__)


class MrrcConfig(object):
    """MrrcConfig is used to store all configurations for mrrc-uploader tools.
    The configuration file will be named as mrrc-uploader.conf, and will be stored
    in $HOME/.mrrc/ folder by default.
    """

    def __init__(self, data: ConfigParser):
        try:
            self.__mrrc_configs = dict(data.items(SECTION_MRRC))
        except NoSectionError:
            pass

    def get_ignore_patterns(self) -> List[str]:
        pattern_str = self.__val_or_default(self.__mrrc_configs, MRRC_IGNORE_PATTERN)
        if pattern_str and pattern_str.strip() != "":
            try:
                return json.loads(pattern_str)
            except (ValueError, TypeError):
                logger.warning("Warning: ignore_patterns %s specified in "
                               "system environment, but not a valid json "
                               "style array. Will skip it.", pattern_str)
        return None

    def __val_or_default(self, section: dict, key: str, default=None):
        return section[key] if section and key in section else default


def mrrc_config():
    parser = ConfigParser()
    config_file = os.path.join(os.environ["HOME"], ".mrrc", CONFIG_FILE)
    if not parser.read(config_file):
        logger.error("Error: not existed config file %s", config_file)
        sys.exit(1)
    return MrrcConfig(parser)
