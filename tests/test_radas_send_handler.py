import tempfile
import os
from unittest import mock
import unittest
from charon.pkgs.radas_signature_handler import sign_in_radas


class RadasSignHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_sign_in_radas_normal_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock configuration
            mock_config = mock.MagicMock()
            mock_config.is_radas_enabled.return_value = True
            mock_radas_config = mock.MagicMock()
            mock_config.get_radas_config.return_value = mock_radas_config

            # Mock Container run to avoid real AMQP connection
            with mock.patch(
                    "charon.pkgs.radas_signature_handler.Container") as mock_container, \
                mock.patch(
                    "charon.pkgs.radas_signature_handler.get_config", return_value=mock_config), \
                mock.patch(
                    "charon.pkgs.radas_signature_handler.uuid.uuid4", return_value="mocked-uuid"):

                test_result_path = os.path.join(tmpdir, "results")
                os.makedirs(test_result_path)

                sign_in_radas(
                    repo_url="quay.io/test/repo",
                    requester="test-user",
                    sign_key="test-key",
                    result_path=test_result_path,
                    ignore_patterns=[],
                    radas_config=mock_radas_config
                )

                # Verify Container.run() was called twice (sender and receiver)
                self.assertEqual(mock_container.call_count, 2)

                # Verify request ID propagation
                receiver_call = mock_container.call_args_list[1]
                self.assertEqual(receiver_call.args[0].request_id, "mocked-uuid")

    def test_sign_in_radas_with_disabled_config(self):
        mock_config = mock.MagicMock()
        mock_config.is_radas_enabled.return_value = False

        with mock.patch(
                "charon.pkgs.radas_signature_handler.get_config", return_value=mock_config), \
                self.assertRaises(SystemExit):

            sign_in_radas(
                repo_url="quay.io/test/repo",
                requester="test-user",
                sign_key="test-key",
                result_path="/tmp/results",
                ignore_patterns=[],
                radas_config=mock.MagicMock()
            )

    def test_sign_in_radas_connection_cleanup(self):
        mock_config = mock.MagicMock()
        mock_config.is_radas_enabled.return_value = True
        mock_radas_config = mock.MagicMock()

        with mock.patch("charon.pkgs.radas_signature_handler.Container") as mock_container, \
             mock.patch("charon.pkgs.radas_signature_handler.get_config", return_value=mock_config):

            mock_sender_conn = mock.MagicMock()
            mock_listener_conn = mock.MagicMock()

            def container_side_effect(*args, **kwargs):
                if args[0].__class__.__name__ == "RadasReceiver":
                    args[0].conn = mock_listener_conn
                elif args[0].__class__.__name__ == "RadasSender":
                    args[0].conn = mock_sender_conn
                return mock.MagicMock()

            mock_container.side_effect = container_side_effect

            sign_in_radas(
                repo_url="quay.io/test/repo",
                requester="test-user",
                sign_key="test-key",
                result_path="/tmp/results",
                ignore_patterns=[],
                radas_config=mock_radas_config
            )

            # Verify connections are closed
            mock_sender_conn.close.assert_called_once()
            mock_listener_conn.close.assert_called_once()
