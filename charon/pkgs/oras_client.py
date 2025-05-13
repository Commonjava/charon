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
import oras.client
import logging
from charon.config import get_config
from typing import List

logger = logging.getLogger(__name__)

class OrasClient:
    """
    Wrapper for oras‑py’s OrasClient, deciding whether to login based on config.
    """

    def __init__(self):
        self.conf = get_config()
        self.client = oras.client.OrasClient()

    def login_if_needed(self) -> None:
        """
        If quay_radas_auth_enabled is true, call login to authenticate.
        """

        if self.conf and self.conf.is_quay_radas_auth_enabled():
            logger.info("Logging in to registry.")
            res = self.client.login(
                hostname=self.conf.get_quay_radas_registry(),
                username=self.conf.get_quay_radas_username(),
                password=self.conf.get_quay_radas_password(),
            )
            logger.info(res)
        else:
            logger.info("Registry auth not enabled, skip login.")

    def pull(self, result_reference_url: str, sign_result_loc: str) -> List[str]:
        """
        Call oras‑py’s pull method to pull the remote file to local.
        Args:
            result_reference_url (str): Reference of the remote file (e.g. “quay.io/repository/signing/radas@hash”).
            sign_result_loc (str): Local save path (e.g. “/tmp/sign”).
        """
        files = []
        try:
            self.login_if_needed()
            # the filename should be possibly named by the digest hash value based on the oras source code
            files = self.client.pull(target=result_reference_url, outdir=sign_result_loc)
            logger.info("Pull file from %s to %s", result_reference_url, sign_result_loc)
        except Exception as e:
            logger.error("Failed to pull file from %s to %s: %s", result_reference_url, sign_result_loc, e)
        finally:
            return files