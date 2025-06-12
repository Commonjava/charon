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
import sys
import asyncio
import uuid
import time
from typing import List, Any, Tuple, Callable, Dict, Optional
from charon.config import RadasConfig
from charon.pkgs.oras_client import OrasClient
from proton import SSLDomain, Message, Event, Sender, Connection
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
        rconf (RadasConfig):
            the configurations for the radas messaging system.
        sign_result_status (str):
            Result of the signing(success/failed)
        sign_result_errors (list):
            Any errors encountered if signing fails, this will be empty list if successful
    """

    def __init__(self, sign_result_loc: str, request_id: str, rconf: RadasConfig) -> None:
        super().__init__()
        self.sign_result_loc = sign_result_loc
        self.request_id = request_id
        self.sign_result_status: Optional[str] = None
        self.sign_result_errors: List[str] = []
        self.rconf = rconf
        self._conn: Optional[Connection] = None
        self._message_handled = False
        self._start_time = 0.0
        self._timeout_check_delay = 30.0
        self._ssl: Optional[SSLDomain] = None
        if rconf.ssl_enabled():
            self._ssl = SSLDomain(SSLDomain.MODE_CLIENT)
            self._ssl.set_trusted_ca_db(self.rconf.root_ca())
            self._ssl.set_peer_authentication(SSLDomain.VERIFY_PEER)
            self._ssl.set_credentials(
                self.rconf.client_ca(),
                self.rconf.client_key(),
                self.rconf.client_key_password()
            )
        self.log = logging.getLogger("charon.pkgs.radas_sign.RadasReceiver")

    def on_start(self, event: Event) -> None:
        umb_target = self.rconf.umb_target()
        container = event.container
        self._conn = container.connect(
            url=umb_target,
            ssl_domain=self._ssl,
            heartbeat=500
        )
        receiver = container.create_receiver(
            context=self._conn, source=self.rconf.result_queue(),
        )
        self.log.info("Listening on %s, queue: %s",
                      umb_target,
                      receiver.source.address)
        self._start_time = time.time()
        container.schedule(self._timeout_check_delay, self)

    def on_timer_task(self, event: Event) -> None:
        current = time.time()
        timeout = self.rconf.receiver_timeout()
        idle_time = current - self._start_time
        self.log.debug("Checking timeout: passed %s seconds, timeout time %s seconds",
                       idle_time, timeout)
        if idle_time > self.rconf.receiver_timeout():
            self.log.error("The receiver did not receive messages for more than %s seconds,"
                           " and needs to stop receiving and quit.", timeout)
            self._close(event)
        else:
            event.container.schedule(self._timeout_check_delay, self)

    def on_message(self, event: Event) -> None:
        self.log.debug("Got message: %s", event.message.body)
        self._process_message(event.message.body)
        if self._message_handled:
            self.log.debug("The signing result is handled.")
            self._close(event)

    def on_error(self, event: Event) -> None:
        self.log.error("Received an error event:\n%s", event.message.body)

    def on_disconnected(self, event: Event) -> None:
        self.log.info("Disconnected from AMQP broker: %s",
                      event.connection.connected_address)

    def _close(self, event: Event) -> None:
        if event:
            if event.connection:
                event.connection.close()
            if event.container:
                event.container.stop()

    def _process_message(self, msg: Any) -> None:
        """
        Process a message received from UMB
        Args:
            msg: The message body received
        """
        msg_dict = json.loads(msg)
        msg_request_id = msg_dict.get("request_id")
        if msg_request_id != self.request_id:
            self.log.info(
                "Message request_id %s does not match the request_id %s from sender, ignoring",
                msg_request_id,
                self.request_id,
            )
            return

        self._message_handled = True
        self.log.info(
            "Start to process the sign event message, request_id %s is matched", msg_request_id
        )
        self.sign_result_status = msg_dict.get("signing_status")
        self.sign_result_errors = msg_dict.get("errors", [])
        if self.sign_result_status == "success":
            result_reference_url = msg_dict.get("result_reference")
            if not result_reference_url:
                self.log.warning("Not found result_reference in message，ignore.")
                return

            self.log.info("Using SIGN RESULT LOC: %s", self.sign_result_loc)
            sign_result_parent_dir = os.path.dirname(self.sign_result_loc)
            os.makedirs(sign_result_parent_dir, exist_ok=True)

            oras_client = OrasClient()
            files = oras_client.pull(
                result_reference_url=result_reference_url, sign_result_loc=self.sign_result_loc
            )
            self.log.info("Number of files pulled: %d, path: %s", len(files), files[0])
        else:
            self.log.error("The signing result received with failed status. Errors: %s",
                           self.sign_result_errors)


class RadasSender(MessagingHandler):
    """
    This simple sender will send given string massage to UMB message queue to request signing.
    Attributes:
        payload (str): payload json string for radas to read,
        this value construct from the cmd flag
        rconf (RadasConfig): the configurations for the radas messaging
        system.
        status (str): tell if status for message sending, only "success"
        means the message is sent successfully.
    """
    def __init__(self, payload: Any, rconf: RadasConfig):
        super(RadasSender, self).__init__()
        self.payload = payload
        self.rconf = rconf
        self.status: Optional[str] = None
        self._message_sent = False  # Flag to track if message was sent
        self._retried = 0
        self._pending: Optional[Message] = None
        self._message: Optional[Message] = None
        self._container: Optional[Container] = None
        self._sender: Optional[Sender] = None
        self._ssl: Optional[SSLDomain] = None
        if self.rconf.ssl_enabled():
            self._ssl = SSLDomain(SSLDomain.MODE_CLIENT)
            self._ssl.set_trusted_ca_db(self.rconf.root_ca())
            self._ssl.set_peer_authentication(SSLDomain.VERIFY_PEER)
            self._ssl.set_credentials(
                self.rconf.client_ca(),
                self.rconf.client_key(),
                self.rconf.client_key_password()
            )
        self.log = logging.getLogger("charon.pkgs.radas_sign.RadasSender")

    def on_start(self, event):
        self._container = event.container
        self.log.debug("Start creating connection for sender")
        conn = self._container.connect(
            url=self.rconf.umb_target(),
            ssl_domain=self._ssl
        )
        self.log.debug("Connection to %s is created.", conn.hostname)
        if conn:
            self._sender = self._container.create_sender(conn, self.rconf.request_channel())

    def on_sendable(self, event):
        if not self._message_sent:
            msg = Message(body=self.payload, durable=True)
            self.log.debug("Sending message: %s to %s", msg.id, event.sender.target.address)
            self._send_msg(msg)
            self._message = msg
            self._message_sent = True

    def on_error(self, event):
        self.log.error("Error happened during message sending, reason %s",
                       event.description)
        self.status = "failed"

    def on_rejected(self, event):
        self._pending = self._message
        self._handle_failed_delivery("Rejected")

    def on_released(self, event):
        self._pending = self._message
        self._handle_failed_delivery("Released")

    def on_accepted(self, event):
        self.log.info("Message accepted by receiver: %s", event.delivery)
        self.status = "success"
        self.close()  # Close connection after confirmation

    def on_timer_task(self, event):
        message_to_retry = self._message
        self._send_msg(message_to_retry)
        self._pending = None

    def close(self):
        self.log.info("Message has been sent successfully, close connection")
        if self._sender:
            self._sender.close()
        if self._container:
            self._container.stop()

    def _send_msg(self, msg: Message):
        if self._sender and self._sender.credit > 0:
            self._sender.send(msg)
            self.log.debug("Message %s sent", msg.id)
        else:
            self.log.warning("Sender not ready or no credit available")

    def _handle_failed_delivery(self, reason: str):
        if self._pending:
            msg = self._pending
            self.log.warning("Message %s failed for reason: %s", msg.id, reason)
            max_retries = self.rconf.radas_sign_timeout_retry_count()
            if self._retried < max_retries:
                # Schedule retry
                self._retried = self._retried + 1
                self.log.info("Scheduling retry %s/%s for message %s",
                              self._retried, max_retries, msg.id)
                # Schedule retry after delay
                if self._container:
                    self._container.schedule(self.rconf.radas_sign_timeout_retry_interval(), self)
            else:
                # Max retries exceeded
                self.log.error("Message %s failed after %s retries", msg.id, max_retries)
                self.status = "failed"
            self._pending = None
        else:
            self.log.info("Message has been sent successfully, close connection")
            self.close()


def generate_radas_sign(top_level: str, sign_result_file: str) -> Tuple[List[str], List[str]]:
    """
    Generate .asc files based on RADAS sign result json file
    """
    if not sign_result_file or not os.path.isfile(sign_result_file):
        logger.error("Sign result file does not exist: %s", sign_result_file)
        return [], []

    # should only have the single sign result json file from the radas registry
    try:
        with open(sign_result_file, "r") as f:
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
    logger.debug("params. repo_url: %s, requester: %s, sign_key: %s, result_path: %s",
                 repo_url, requester, sign_key, result_path)
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

    sender = RadasSender(json.dumps(payload), radas_config)
    container = Container(sender)
    container.run()

    if not sender.status == "success":
        logger.error("Something wrong happened in message sending, see logs")
        sys.exit(1)

    # request_id = "some-request-id-1" # for test purpose
    receiver = RadasReceiver(result_path, request_id, radas_config)
    Container(receiver).run()

    status = receiver.sign_result_status
    if status != "success":
        logger.error("The signing result is processed with errors: %s",
                     receiver.sign_result_errors)
        sys.exit(1)
