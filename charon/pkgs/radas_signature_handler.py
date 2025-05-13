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
import proton
import proton.handlers
import threading
import logging
import json
import os
import asyncio
from typing import List, Any, Tuple, Callable, Dict
from charon.config import get_config
from charon.constants import DEFAULT_SIGN_RESULT_LOC
from charon.constants import DEFAULT_RADAS_SIGN_TIMEOUT_COUNT
from charon.constants import DEFAULT_RADAS_SIGN_WAIT_INTERVAL_SEC
from charon.pkgs.oras_client import OrasClient

logger = logging.getLogger(__name__)

class SignHandler:
    """
    Handle the sign result status management
    """
    _is_processing: bool = True
    _downloaded_files: List[str] = []

    @classmethod
    def is_processing(cls) -> bool:
        return cls._is_processing

    @classmethod
    def get_downloaded_files(cls) -> List[str]:
        return cls._downloaded_files.copy()

    @classmethod
    def set_processing(cls, value: bool) -> None:
        cls._is_processing = value

    @classmethod
    def set_downloaded_files(cls, files: List[str]) -> None:
        cls._downloaded_files = files

class UmbListener(proton.handlers.MessagingHandler):
    """
    UmbListener class (AMQP version), register this when setup UmbClient
    """

    def __init__(self) -> None:
        super().__init__()

    def on_start(self, event: proton.Event) -> None:
        """
        On start callback
        """
        conf = get_config()
        if not conf:
            sys.exit(1)
        event.container.create_receiver(conf.get_amqp_queue())

    def on_message(self, event: proton.Event) -> None:
        """
        On message callback
        """
        # handle response from radas in a thread
        thread = threading.Thread(
            target=self._process_message,
            args=[event.message.body]
        )
        thread.start()

    def on_error(self, event: proton.Event) -> None:
        """
        On error callback
        """
        logger.error("Received an error event:\n%s", event)

    def on_disconnected(self, event: proton.Event) -> None:
        """
        On disconnected callback
        """
        logger.error("Disconnected from AMQP broker.")

    def _process_message(msg: Any) -> None:
        """
        Process a message received from UMB
        Args:
            msg: The message body received
        """
        try:
            msg_dict = json.loads(msg)
            result_reference_url = msg_dict.get("result_reference")

            if not result_reference_url:
                 logger.warning("Not found result_reference in message，ignore.")
                 return

            conf = get_config()
            if not conf:
                sign_result_loc = DEFAULT_SIGN_RESULT_LOC
            sign_result_loc = os.getenv("SIGN_RESULT_LOC") or conf.get_sign_result_loc()
            logger.info("Using SIGN RESULT LOC: %s", sign_result_loc)

            sign_result_parent_dir = os.path.dirname(sign_result_loc)
            os.makedirs(sign_result_parent_dir, exist_ok=True)

            oras_client = OrasClient()
            files = oras_client.pull(
                result_reference_url=result_reference_url,
                sign_result_loc=sign_result_loc
            )
            SignHandler.set_downloaded_files(files)
        finally:
            SignHandler.set_processing(False)

def generate_radas_sign(top_level: str) -> Tuple[List[str], List[str]]:
    """
    Generate .asc files based on RADAS sign result json file
    """
    conf = get_config()
    timeout_count = conf.get_radas_sign_timeout_count() if conf else DEFAULT_RADAS_SIGN_TIMEOUT_COUNT
    wait_interval_sec = conf.get_radas_sign_wait_interval_sec() if conf else DEFAULT_RADAS_SIGN_WAIT_INTERVAL_SEC
    wait_count = 0
    while SignHandler.is_processing():
        wait_count += 1
        if wait_count > timeout_count:
            logger.warning("Timeout when waiting for sign response.")
            break
        time.sleep(wait_interval_sec)

    files = SignHandler.get_downloaded_files()
    if not files:
        return [], []

    # should only have the single sign result json file from the radas registry
    json_file_path = files[0]
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read or parse the JSON file: {e}")
        raise

    async def generate_single_sign_file(
        file_path: str, signature: str, failed_paths: List[str], generated_signs: List[str],
        sem: asyncio.BoundedSemaphore
    ):
        async with sem:
            if not file_path or not signature:
                logger.error(f"Invalid JSON entry")
                return
            # remove the root path maven-repository
            filename = file_path.split("/", 1)[1]
            signature = item.get("signature")

            artifact_path = os.path.join(top_level, filename)
            asc_filename = f"{filename}.asc"
            signature_path = os.path.join(top_level, asc_filename)

            if not os.path.isfile(artifact_path):
                logger.warning("Artifact missing, skip signature file generation")
                return

            try:
                with open(signature_path, 'w') as asc_file:
                    asc_file.write(signature)
                generated_signs.append(signature_path)
                logger.info(f"Generated .asc file: {signature_path}")
            except Exception as e:
                failed_paths.append(signature_path)
                logger.error(f"Failed to write .asc file for {artifact_path}: {e}")

    result = data.get("result", [])
    return __do_path_cut_and(
            path_handler=generate_single_sign_file,
            data=result
        )

def __do_path_cut_and(
    path_handler: Callable,
    data: List[Dict[str, str]]
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