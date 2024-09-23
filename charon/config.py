"""
Copyright (C) 2022 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
import logging
import os
from typing import Dict, List, Optional

from charon.utils.yaml import read_yaml_from_file_path

CONFIG_FILE = "charon.yaml"

logger = logging.getLogger(__name__)


class CharonConfig(object):
    """CharonConfig is used to store all configurations for charon
    tools.
    The configuration file will be named as charon.yaml, and will be stored
    in $HOME/.charon/ folder by default.
    """

    def __init__(self, data: Dict):
        self.__ignore_patterns: List[str] = data.get("ignore_patterns", None)
        self.__aws_profile: str = data.get("aws_profile", None)
        self.__targets: Dict = data.get("targets", None)
        self.__manifest_bucket: str = data.get("manifest_bucket", None)
        self.__ignore_signature_suffix: Dict = data.get("ignore_signature_suffix", None)
        self.__signature_command: str = data.get("detach_signature_command", None)
        self.__aws_cf_enable: bool = data.get("aws_cf_enable", False)

    def get_ignore_patterns(self) -> List[str]:
        return self.__ignore_patterns

    def get_target(self, target: str) -> List[Dict]:
        target_: List = self.__targets.get(target, [])
        if not target_:
            logger.error("The target %s is not found in charon configuration.", target)
        return target_

    def get_aws_profile(self) -> str:
        return self.__aws_profile

    def get_manifest_bucket(self) -> str:
        return self.__manifest_bucket

    def get_ignore_signature_suffix(self, package_type: str) -> List[str]:
        xartifact_list: List = self.__ignore_signature_suffix.get(package_type)
        if not xartifact_list:
            logger.error("package type %s does not have ignore artifact config.", package_type)
        return xartifact_list

    def get_detach_signature_command(self) -> str:
        return self.__signature_command

    def is_aws_cf_enable(self) -> bool:
        return self.__aws_cf_enable


def get_config(cfgPath=None) -> Optional[CharonConfig]:
    config_file_path = cfgPath
    if not config_file_path or not os.path.isfile(config_file_path):
        config_file_path = os.path.join(os.getenv("HOME"), ".charon", CONFIG_FILE)
    data = read_yaml_from_file_path(config_file_path, 'schemas/charon.json')
    return CharonConfig(data)


def get_template(template_file: str) -> str:
    template = os.path.join(
        os.getenv("HOME", ''), ".charon/template", template_file
    )
    if os.path.isfile(template):
        with open(template, encoding="utf-8") as file_:
            return file_.read()
    raise FileNotFoundError
