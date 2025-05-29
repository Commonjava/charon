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
import uuid
from typing import List, Any, Tuple, Callable, Dict, Optional
from charon.config import get_config, RadasConfig
from charon.pkgs.oras_client import OrasClient
from proton import SSLDomain, Message, Event
from proton.handlers import MessagingHandler
from proton.reactor import Container

logger = logging.getLogger(__name__)


class RadasReceiver(MessagingHandler):
    """
    This receiver will listen to UMB message queue to receive signing message for
    signing result.
    Attributes:
        sign_result_loc (str):
            Local save path (e.g. “/tmp/sign”) for oras pull result, this value transfers
            from the cmd flag,should register UmbListener when the client starts
        request_id (str):
            Identifier of the request for the signing result
        sign_result_status (str):
            Result of the signing(success/failed)
        sign_result_errors (list):
            Any errors encountered if signing fails, this will be empty list if successful
    """

    def __init__(self, sign_result_loc: str, request_id: str) -> None:
        super().__init__()
        self.sign_result_loc = sign_result_loc
        self.request_id = request_id
        self.conn = None
        self.sign_result_status: Optional[str] = None
        self.sign_result_errors: List[str] = []

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

        ssl_domain = SSLDomain(SSLDomain.MODE_CLIENT)
        ssl_domain.set_credentials(
            rconf.client_ca(),
            rconf.client_key(),
            rconf.client_key_password()
        )
        ssl_domain.set_trusted_ca_db(rconf.root_ca())
        ssl_domain.set_peer_authentication(SSLDomain.VERIFY_PEER)

        self.conn = event.container.connect(
            url=rconf.umb_target(),
            ssl_domain=ssl_domain
        )
        event.container.create_receiver(
            self.conn, rconf.result_queue(), dynamic=True
        )
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
        msg_request_id = msg_dict.get("request_id")
        if msg_request_id != self.request_id:
            logger.info(
                "Message request_id %s does not match the request_id %s from sender, ignoring",
                msg_request_id,
                self.request_id,
            )
            return

        logger.info(
            "Start to process the sign event message, request_id %s is matched", msg_request_id
        )
        self.sign_result_status = msg_dict.get("signing_status")
        self.sign_result_errors = msg_dict.get("errors", [])
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


class RadasSender(MessagingHandler):
    """
    This simple sender will send given string massage to UMB message queue to request signing.
    Attributes:
        payload (str): payload json string for radas to read,
        this value construct from the cmd flag
    """
    def __init__(self, payload: str):
        super().__init__()
        self.payload = payload
        self.container = None
        self.conn = None
        self.sender = None

    def on_start(self, event):
        """
        On start callback
        """
        conf = get_config()
        if not (conf and conf.is_radas_enabled()):
            sys.exit(1)

        rconf = conf.get_radas_config()
        if rconf is None:
            sys.exit(1)

        ssl_domain = SSLDomain(SSLDomain.MODE_CLIENT)
        ssl_domain.set_credentials(
            rconf.client_ca(),
            rconf.client_key(),
            rconf.client_key_password()
        )
        ssl_domain.set_trusted_ca_db(rconf.root_ca())
        ssl_domain.set_peer_authentication(SSLDomain.VERIFY_PEER)

        self.container = event.container
        self.conn = event.container.connect(
            url=rconf.umb_target(),
            ssl_domain=ssl_domain
        )
        self.sender = event.container.create_sender(self.conn, rconf.request_queue())

    def on_sendable(self):
        """
        On message able to send callback
        """
        request = self.payload
        msg = Message(body=request)
        if self.sender:
            self.sender.send(msg)
        if self.container:
            self.container.stop()


def generate_radas_sign(top_level: str, sign_result_loc: str) -> Tuple[List[str], List[str]]:
    """
    Generate .asc files based on RADAS sign result json file
    """
    if not os.path.isdir(sign_result_loc):
        logger.error("Sign result loc dir does not exist: %s", sign_result_loc)
        return [], []

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

    result = data.get("results", [])
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


def sign_in_radas(repo_url: str,
                  requester: str,
                  sign_key: str,
                  result_path: str,
                  ignore_patterns: List[str],
                  radas_config: RadasConfig):
    """
    This function will be responsible to do the overall controlling of the whole process,
    like trigger the send and register the receiver, and control the wait and timeout there.
    """
    logger.debug("params. repo_url: %s, requester: %s, sign_key: %s, result_path: %s,"
                 "radas_config: %s", repo_url, requester, sign_key, result_path, radas_config)
    request_id = str(uuid.uuid4())
    exclude = ignore_patterns if ignore_patterns else []

    payload = {
        "request_id": request_id,
        "requested_by": requester,
        "type": "mrrc",
        "file_reference": repo_url,
        "sig_keyname": sign_key,
        "exclude": exclude
    }

    listener = RadasReceiver(result_path, request_id)
    sender = RadasSender(json.dumps(payload))

    try:
        Container(sender).run()
        logger.info("Successfully sent signing request ID: %s", request_id)
        Container(listener).run()
    finally:
        if listener.conn is not None:
            listener.conn.close()
        if sender.conn is not None:
            sender.conn.close()
