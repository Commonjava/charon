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
import json
import os
import asyncio
import sys
from typing import List, Any, Tuple, Callable, Dict
from charon.config import get_config
from charon.pkgs.oras_client import OrasClient
from proton import Event
from proton.handlers import MessagingHandler

logger = logging.getLogger(__name__)


class UmbListener(MessagingHandler):
    """
    UmbListener class (AMQP version), register this when setup UmbClient
    Attributes:
        sign_result_loc (str): Local save path (e.g. “/tmp/sign”) for oras pull result,
        this value transfers from the cmd flag, should register UmbListener when the client starts
    """

    def __init__(self, sign_result_loc: str) -> None:
        super().__init__()
        self.sign_result_loc = sign_result_loc

    def on_start(self, event: Event) -> None:
        """
        On start callback
        """
        conf = get_config()
        if not (conf and conf.is_radas_enabled()):
            sys.exit(1)

        rconf = conf.get_radas_config()
        # explicit check to pass the type checker
        if rconf is None:
            sys.exit(1)
        conn = event.container.connect(rconf.umb_target())
        event.container.create_receiver(conn, rconf.result_queue())
        logger.info("Listening on %s, queue: %s", rconf.umb_target(), rconf.result_queue())

    def on_message(self, event: Event) -> None:
        """
        On message callback
        """
        self._process_message(event.message.body)

    def on_connection_error(self, event: Event) -> None:
        """
        On connection error callback
        """
        logger.error("Received an error event:\n%s", event)

    def on_disconnected(self, event: Event) -> None:
        """
        On disconnected callback
        """
        logger.error("Disconnected from AMQP broker.")

    def _process_message(self, msg: Any) -> None:
        """
        Process a message received from UMB
        Args:
            msg: The message body received
        """
        msg_dict = json.loads(msg)
        result_reference_url = msg_dict.get("result_reference")

        if not result_reference_url:
            logger.warning("Not found result_reference in message，ignore.")
            return

        logger.info("Using SIGN RESULT LOC: %s", self.sign_result_loc)
        sign_result_parent_dir = os.path.dirname(self.sign_result_loc)
        os.makedirs(sign_result_parent_dir, exist_ok=True)

        oras_client = OrasClient()
        files = oras_client.pull(
            result_reference_url=result_reference_url, sign_result_loc=self.sign_result_loc
        )
        logger.info("Number of files pulled: %d, path: %s", len(files), files[0])


def generate_radas_sign(top_level: str, sign_result_loc: str) -> Tuple[List[str], List[str]]:
    """
    Generate .asc files based on RADAS sign result json file
    """
    files = [
        os.path.join(sign_result_loc, f)
        for f in os.listdir(sign_result_loc)
        if os.path.isfile(os.path.join(sign_result_loc, f))
    ]

    if not files:
        return [], []

    if len(files) > 1:
        logger.error("Multiple files found in %s. Expected only one file.", sign_result_loc)
        return [], []

    # should only have the single sign result json file from the radas registry
    json_file_path = files[0]
    try:
        with open(json_file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to read or parse the JSON file: %s", e)
        raise

    async def generate_single_sign_file(
        file_path: str,
        signature: str,
        failed_paths: List[str],
        generated_signs: List[str],
        sem: asyncio.BoundedSemaphore,
    ):
        async with sem:
            if not file_path or not signature:
                logger.error("Invalid JSON entry")
                return
            # remove the root path maven-repository
            filename = file_path.split("/", 1)[1]

            artifact_path = os.path.join(top_level, filename)
            asc_filename = f"{filename}.asc"
            signature_path = os.path.join(top_level, asc_filename)

            if not os.path.isfile(artifact_path):
                logger.warning("Artifact missing, skip signature file generation")
                return

            try:
                with open(signature_path, "w") as asc_file:
                    asc_file.write(signature)
                generated_signs.append(signature_path)
                logger.info("Generated .asc file: %s", signature_path)
            except Exception as e:
                failed_paths.append(signature_path)
                logger.error("Failed to write .asc file for %s: %s", artifact_path, e)

    result = data.get("result", [])
    return __do_path_cut_and(path_handler=generate_single_sign_file, data=result)


def __do_path_cut_and(
    path_handler: Callable, data: List[Dict[str, str]]
) -> Tuple[List[str], List[str]]:

    failed_paths: List[str] = []
    generated_signs: List[str] = []
    tasks = []
    sem = asyncio.BoundedSemaphore(10)
    for item in data:
        file_path = item.get("file")
        signature = item.get("signature")
        tasks.append(
            asyncio.ensure_future(
                path_handler(file_path, signature, failed_paths, generated_signs, sem)
            )
        )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))
    return (failed_paths, generated_signs)
