from unittest import mock
import unittest
import tempfile
import time
import json
from charon.pkgs.radas_sign import RadasReceiver


class RadasSignReceiverTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def reset_receiver(self, r_receiver: RadasReceiver) -> None:
        r_receiver.message_handled = False
        r_receiver.sign_result_errors = []
        r_receiver.sign_result_status = None

    def test_radas_receiver(self):
        # Mock configuration
        mock_radas_config = mock.MagicMock()
        mock_radas_config.validate.return_value = True
        mock_radas_config.client_ca.return_value = "test-client-ca"
        mock_radas_config.client_key.return_value = "test-client-key"
        mock_radas_config.client_key_password.return_value = "test-client-key-pass"
        mock_radas_config.root_ca.return_value = "test-root-ca"
        mock_radas_config.receiver_timeout.return_value = 60

        # Mock Container run to avoid real AMQP connection
        with mock.patch(
                "charon.pkgs.radas_sign.Container") as mock_container, \
                mock.patch("charon.pkgs.radas_sign.SSLDomain") as ssl_domain, \
                mock.patch("charon.pkgs.radas_sign.OrasClient") as oras_client, \
                mock.patch("charon.pkgs.radas_sign.Event") as event:
            test_result_path = tempfile.mkdtemp()
            test_request_id = "test-request-id"
            r_receiver = RadasReceiver(test_result_path, test_request_id, mock_radas_config)
            self.assertEqual(ssl_domain.call_count, 1)
            self.assertEqual(r_receiver.sign_result_loc, test_result_path)
            self.assertEqual(r_receiver.request_id, test_request_id)

            # prepare mock
            mock_receiver = mock.MagicMock()
            mock_conn = mock.MagicMock()
            mock_container.connect.return_value = mock_conn
            mock_container.create_receiver.return_value = mock_receiver
            event.container = mock_container
            event.message = mock.MagicMock()
            event.connection = mock.MagicMock()

            # test on_start
            r_receiver.on_start(event)
            self.assertEqual(mock_container.connect.call_count, 1)
            self.assertEqual(mock_container.create_receiver.call_count, 1)
            self.assertTrue(r_receiver.start_time > 0.0)
            self.assertTrue(r_receiver.start_time < time.time())
            self.assertEqual(mock_container.schedule.call_count, 1)

            # test on_message: unmatched case
            test_ummatch_result = {
                "request_id": "test-request-id-no-match",
                "file_reference": "quay.io/example/test-repo",
                "result_reference": "quay.io/example-sign/sign-repo",
                "sig_keyname": "testkey",
                "signing_status": "success",
                "errors": []
            }
            event.message.body = json.dumps(test_ummatch_result)
            r_receiver.on_message(event)
            self.assertEqual(event.connection.close.call_count, 0)
            self.assertEqual(mock_container.stop.call_count, 0)
            self.assertFalse(r_receiver.message_handled)
            self.assertIsNone(r_receiver.sign_result_status)
            self.assertEqual(r_receiver.sign_result_errors, [])
            self.assertEqual(oras_client.call_count, 0)

            # test on_message: matched case with failed status
            self.reset_receiver(r_receiver)
            test_failed_result = {
                "request_id": "test-request-id",
                "file_reference": "quay.io/example/test-repo",
                "result_reference": "quay.io/example-sign/sign-repo",
                "sig_keyname": "testkey",
                "signing_status": "failed",
                "errors": ["error1", "error2"]
            }
            event.message.body = json.dumps(test_failed_result)
            r_receiver.on_message(event)
            self.assertEqual(event.connection.close.call_count, 1)
            self.assertEqual(mock_container.stop.call_count, 1)
            self.assertTrue(r_receiver.message_handled)
            self.assertEqual(r_receiver.sign_result_status, "failed")
            self.assertEqual(r_receiver.sign_result_errors, ["error1", "error2"])
            self.assertEqual(oras_client.call_count, 0)

            # test on_message: matched case with success status
            self.reset_receiver(r_receiver)
            test_success_result = {
                "request_id": "test-request-id",
                "file_reference": "quay.io/example/test-repo",
                "result_reference": "quay.io/example-sign/sign-repo",
                "sig_keyname": "testkey",
                "signing_status": "success",
                "errors": []
            }
            event.message.body = json.dumps(test_success_result)
            r_receiver.on_message(event)
            self.assertEqual(event.connection.close.call_count, 2)
            self.assertEqual(mock_container.stop.call_count, 2)
            self.assertTrue(r_receiver.message_handled)
            self.assertEqual(r_receiver.sign_result_status, "success")
            self.assertEqual(r_receiver.sign_result_errors, [])
            self.assertEqual(oras_client.call_count, 1)
            oras_client_call = oras_client.return_value
            self.assertEqual(oras_client_call.pull.call_count, 1)

            # test on_timer_task: not timeout
            r_receiver.on_timer_task(event)
            self.assertEqual(event.connection.close.call_count, 2)
            self.assertEqual(mock_container.stop.call_count, 2)
            self.assertEqual(mock_container.schedule.call_count, 2)

            # test on_timer_task: timeout
            mock_radas_config.receiver_timeout.return_value = 0
            r_receiver.on_timer_task(event)
            self.assertEqual(event.connection.close.call_count, 3)
            self.assertEqual(mock_container.stop.call_count, 3)
            self.assertEqual(mock_container.schedule.call_count, 2)
