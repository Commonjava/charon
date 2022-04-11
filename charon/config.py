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
from typing import Dict, List
from ruamel.yaml import YAML
from pathlib import Path
import os
import logging

from charon.utils.strings import remove_prefix
from charon.constants import DEFAULT_REGISTRY

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
        if not self.__targets or not isinstance(self.__targets, Dict):
            raise TypeError("Charon configuration is not correct: targets is invalid.")
        self.__manifest_bucket: str = data.get("manifest_bucket", None)

    def get_ignore_patterns(self) -> List[str]:
        return self.__ignore_patterns

    def get_aws_profile(self) -> str:
        return self.__aws_profile

    def get_aws_bucket(self, target: str) -> str:
        target_: Dict = self.__targets.get(target, None)
        if not target_ or not isinstance(target_, Dict):
            logger.error("The target %s is not found in charon configuration.", target)
            return None
        bucket = target_.get("bucket", None)
        if not bucket:
            logger.error("The bucket is not found for target %s "
                         "in charon configuration.", target)
        return bucket

    def get_bucket_prefix(self, target: str) -> str:
        target_: Dict = self.__targets.get(target, None)
        if not target_ or not isinstance(target_, Dict):
            logger.error("The target %s is not found in charon "
                         "configuration.", target)
            return None
        prefix = target_.get("prefix", None)
        if not prefix:
            logger.warning("The prefix is not found for target %s "
                           "in charon configuration, so no prefix will "
                           "be used", target)
            prefix = ""
        # removing first slash as it is not needed.
        prefix = remove_prefix(prefix, "/")
        return prefix

    def get_bucket_registry(self, target: str) -> str:
        target_: Dict = self.__targets.get(target, None)
        if not target_ or not isinstance(target_, Dict):
            logger.error("The target %s is not found in charon configuration.", target)
            return None
        registry = target_.get("registry", None)
        if not registry:
            registry = DEFAULT_REGISTRY
            logger.error("The registry is not found for target %s "
                         "in charon configuration, so DEFAULT_REGISTRY(localhost) will be used.",
                         target)
        return registry

    def get_manifest_bucket(self) -> str:
        return self.__manifest_bucket


def get_config() -> CharonConfig:
    config_file = os.path.join(os.getenv("HOME"), ".charon", CONFIG_FILE)
    try:
        yaml = YAML(typ='safe')
        data = yaml.load(stream=Path(config_file))
    except Exception as e:
        logger.error("Can not load charon config file due to error: %s", e)
        return None
    try:
        return CharonConfig(data)
    except TypeError as e:
        logger.error(e)
        return None


def get_template(template_file: str) -> str:
    template = os.path.join(
        os.getenv("HOME"), ".charon/template", template_file
    )
    if os.path.isfile(template):
        with open(template, encoding="utf-8") as file_:
            return file_.read()
    raise FileNotFoundError
