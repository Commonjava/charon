"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/hermes)

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
import logging
import json

CONFIG_FILE = "hermes.conf"

SECTION_HERMES = "hermes"
IGNORE_PATTERN = "ignore_patterns"

AWS_BUCKET = "bucket"
AWS_DEFAULT_BUCKET = "hermes"


logger = logging.getLogger(__name__)


class HermesConfig(object):
    """HermesConfig is used to store all configurations for hermes
    tools.
    The configuration file will be named as hermes.conf, and will be stored
    in $HOME/.hermes/ folder by default.
    """
    def __init__(self, data: ConfigParser):
        try:
            self.__hermes_configs = dict(data.items(SECTION_HERMES))
        except NoSectionError:
            pass

    def get_ignore_patterns(self) -> List[str]:
        pattern_str = self.__val_or_default(self.__hermes_configs, IGNORE_PATTERN)
        if pattern_str and pattern_str.strip() != "":
            try:
                return json.loads(pattern_str)
            except (ValueError, TypeError):
                logger.warning("Warning: ignore_patterns %s specified in "
                               "system environment, but not a valid json "
                               "style array. Will skip it.", pattern_str)
        return None

    def get_aws_bucket(self) -> str:
        bucket = self.__val_or_default(self.__hermes_configs, AWS_BUCKET)
        if not bucket:
            logger.warning("%s not defined in hermes configuration,"
                           " will use default 'hermes' bucket.", AWS_BUCKET)
            return AWS_DEFAULT_BUCKET
        return bucket

    def __val_or_default(self, section: dict, key: str, default=None):
        if not section:
            return default
        return section[key] if section and key in section else default


def get_config():
    parser = ConfigParser()
    config_file = os.path.join(os.getenv("HOME"), ".hermes", CONFIG_FILE)
    if not parser.read(config_file):
        logger.warning("Warning: config file does not exist: %s", config_file)
        return None
    return HermesConfig(parser)


def get_template(template_file: str) -> str:
    template = os.path.join(
        os.getenv("HOME"), ".hermes/template", template_file
    )
    if os.path.isfile(template):
        with open(template, encoding="utf-8") as file_:
            return file_.read()

    raise FileNotFoundError
