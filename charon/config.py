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


class RadasConfig(object):
    def __init__(self, data: Dict):
        self.__umb_host: str = data.get("umb_host", None)
        self.__umb_host_port: str = data.get("umb_host_port", "5671")
        self.__result_queue: str = data.get("result_queue", None)
        self.__request_queue: str = data.get("request_queue", None)
        self.__client_ca: str = data.get("client_ca", None)
        self.__client_key: str = data.get("client_key", None)
        self.__client_key_pass_file: str = data.get("client_key_pass_file", None)
        self.__root_ca: str = data.get("root_ca", "/etc/pki/tls/certs/ca-bundle.crt")
        self.__quay_radas_registry_config: Optional[str] = data.get(
            "quay_radas_registry_config", None
        )
        self.__radas_sign_timeout_retry_count: int = data.get("radas_sign_timeout_retry_count", 10)
        self.__radas_sign_timeout_retry_interval: int = data.get(
            "radas_sign_timeout_retry_interval", 60
        )
        self.__radas_receiver_timeout: int = int(data.get("radas_receiver_timeout", 1800))

    def validate(self) -> bool:
        if not self.__umb_host:
            logger.error("Missing host name setting for UMB!")
            return False
        if not self.__result_queue:
            logger.error("Missing the queue setting to receive signing result in UMB!")
            return False
        if not self.__request_queue:
            logger.error("Missing the queue setting to send signing request in UMB!")
            return False
        if self.__client_ca and not os.access(self.__client_ca, os.R_OK):
            logger.error("The client CA file is not valid!")
            return False
        if self.__client_key and not os.access(self.__client_key, os.R_OK):
            logger.error("The client key file is not valid!")
            return False
        if self.__client_key_pass_file and not os.access(self.__client_key_pass_file, os.R_OK):
            logger.error("The client key password file is not valid!")
            return False
        if self.__root_ca and not os.access(self.__root_ca, os.R_OK):
            logger.error("The root ca file is not valid!")
            return False
        if self.__quay_radas_registry_config and not os.access(
            self.__quay_radas_registry_config, os.R_OK
        ):
            self.__quay_radas_registry_config = None
            logger.warning(
                "The quay registry config for oras is not valid, will ignore the registry config!"
            )
        return True

    def umb_target(self) -> str:
        return f"amqps://{self.__umb_host.strip()}:{self.__umb_host_port}"

    def result_queue(self) -> str:
        return self.__result_queue.strip()

    def request_queue(self) -> str:
        return self.__request_queue.strip()

    def client_ca(self) -> str:
        return self.__client_ca.strip()

    def client_key(self) -> str:
        return self.__client_key.strip()

    def client_key_password(self) -> str:
        pass_file = self.__client_key_pass_file
        if os.access(pass_file, os.R_OK):
            with open(pass_file, "r") as f:
                return f.read().strip()
        elif pass_file:
            logger.warning("The key password file is not accessible. Will ignore the password.")
        return ""

    def root_ca(self) -> str:
        return self.__root_ca.strip()

    def quay_radas_registry_config(self) -> Optional[str]:
        if self.__quay_radas_registry_config:
            return self.__quay_radas_registry_config.strip()
        return None

    def radas_sign_timeout_retry_count(self) -> int:
        return self.__radas_sign_timeout_retry_count

    def radas_sign_timeout_retry_interval(self) -> int:
        return self.__radas_sign_timeout_retry_interval

    def receiver_timeout(self) -> int:
        return self.__radas_receiver_timeout


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
        radas_config: Dict = data.get("radas", None)
        self.__radas_config: Optional[RadasConfig] = None
        if radas_config:
            self.__radas_config = RadasConfig(radas_config)
            self.__radas_enabled = bool(self.__radas_config and self.__radas_config.validate())
        else:
            self.__radas_enabled = False

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

    def get_ignore_signature_suffix(self, package_type: str) -> Optional[List[str]]:
        xartifact_list = self.__ignore_signature_suffix.get(package_type)
        if not xartifact_list:
            logger.error("package type %s does not have ignore artifact config.", package_type)
        return xartifact_list

    def get_detach_signature_command(self) -> str:
        return self.__signature_command

    def is_aws_cf_enable(self) -> bool:
        return self.__aws_cf_enable

    def is_radas_enabled(self) -> bool:
        return self.__radas_enabled

    def get_radas_config(self) -> Optional[RadasConfig]:
        return self.__radas_config


def get_config(cfgPath=None) -> CharonConfig:
    config_file_path = cfgPath
    if not config_file_path or not os.path.isfile(config_file_path):
        config_file_path = os.path.join(os.getenv("HOME", ""), ".charon", CONFIG_FILE)
    data = read_yaml_from_file_path(config_file_path, "schemas/charon.json")
    return CharonConfig(data)


def get_template(template_file: str) -> str:
    template = os.path.join(os.getenv("HOME", ""), ".charon/template", template_file)
    if os.path.isfile(template):
        with open(template, encoding="utf-8") as file_:
            return file_.read()
    raise FileNotFoundError
