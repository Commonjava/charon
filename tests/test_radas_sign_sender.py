import json
from unittest import mock
import unittest
from charon.pkgs.radas_sign import RadasSender


class RadasSignSenderTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_radas_sender(self):
        # Mock configuration
        mock_radas_config = mock.MagicMock()
        mock_radas_config.validate.return_value = True
        mock_radas_config.client_ca.return_value = "test-client-ca"
        mock_radas_config.client_key.return_value = "test-client-key"
        mock_radas_config.client_key_password.return_value = "test-client-key-pass"
        mock_radas_config.root_ca.return_value = "test-root-ca"
        mock_radas_config.radas_sign_timeout_retry_count.return_value = 5

        test_payload = {
            "request_id": "mock-id",
            "requested_by": "test-user",
            "type": "mrrc",
            "file_reference": "quay.io/test/repo",
            "sig_keyname": "test-key",
            "exclude": []
        }

        # Mock Container run to avoid real AMQP connection
        with mock.patch(
                "charon.pkgs.radas_sign.Container") as mock_container, \
                mock.patch("charon.pkgs.radas_sign.SSLDomain") as ssl_domain, \
                mock.patch("charon.pkgs.radas_sign.Event") as event:

            json_payload = json.dumps(test_payload)
            r_sender = RadasSender(json_payload, mock_radas_config)
            self.assertEqual(ssl_domain.call_count, 1)
            self.assertEqual(r_sender.payload, json_payload)
            self.assertIs(r_sender.rconf, mock_radas_config)
            self.assertIsNone(r_sender._message)
            self.assertIsNone(r_sender._pending)

            # test on_start
            mock_sender = mock.MagicMock()
            mock_conn = mock.MagicMock()
            mock_container.connect.return_value = mock_conn
            mock_container.create_sender.return_value = mock_sender
            event.container = mock_container
            r_sender.on_start(event)
            self.assertEqual(mock_container.connect.call_count, 1)
            self.assertEqual(mock_container.create_sender.call_count, 1)

            # test on_sendable
            mock_sender.credit = 1
            r_sender.on_sendable(event)
            self.assertIsNotNone(r_sender._message)
            self.assertEqual(mock_sender.send.call_count, 1)

            # test on_accepted
            r_sender.on_accepted(event)
            self.assertEqual(r_sender.status, "success")
            self.assertEqual(r_sender._retried, 0)
            self.assertEqual(r_sender._sender.close.call_count, 1)
            self.assertEqual(r_sender._container.stop.call_count, 1)

            # test on_rejected
            r_sender.on_rejected(event)
            self.assertIsNone(r_sender._pending)
            self.assertEqual(r_sender._retried, 1)
            self.assertEqual(r_sender._container.schedule.call_count, 1)

            # test on_released
            r_sender.on_released(event)
            self.assertIsNone(r_sender._pending)
            self.assertEqual(r_sender._retried, 2)
            self.assertEqual(r_sender._container.schedule.call_count, 2)

            # test on_released
            r_sender.on_timer_task(event)
            self.assertIsNone(r_sender._pending)
            self.assertEqual(r_sender._retried, 2)
            self.assertEqual(mock_sender.send.call_count, 2)
