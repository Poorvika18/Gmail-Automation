import unittest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime
import pickle
import os
from core.gmail_service import GmailProcessor


class TestGmailProcessor(unittest.TestCase):

    def setUp(self):
        self.gp = GmailProcessor(
            credentials_file="core/credentials.json",
            token_file="core/token.pickle"
        )

    def test_iso_from_internal_date_valid(self):
        ms = str(int(datetime(2025, 1, 1).timestamp() * 1000))
        result = self.gp.iso_from_internal_date(ms)
        self.assertEqual(result.year, 2025)

    def test_iso_from_internal_date_invalid(self):
        result = self.gp.iso_from_internal_date("invalid")
        self.assertIsNone(result)

    @patch("core.gmail_service.build")
    @patch("core.gmail_service.pickle.load")
    @patch("core.gmail_service.os.path.exists", return_value=True)
    def test_get_gmail_service_with_existing_token(self, mock_exists, mock_pickle, mock_build):
        creds_mock = MagicMock()
        creds_mock.valid = True
        mock_pickle.return_value = creds_mock
        mock_build.return_value = "gmail_service"

        result = self.gp.get_gmail_service()
        self.assertEqual(result, "gmail_service")
        mock_build.assert_called_once()

    @patch("core.gmail_service.build")
    @patch("core.gmail_service.pickle.dump")
    @patch("core.gmail_service.os.path.exists", return_value=False)
    @patch("core.gmail_service.InstalledAppFlow.from_client_secrets_file")
    def test_get_gmail_service_new_credentials(self, mock_flow, mock_exists, mock_pickle_dump, mock_build):
        flow_mock = MagicMock()
        flow_mock.run_local_server.return_value = MagicMock(valid=True)
        mock_flow.return_value = flow_mock
        mock_build.return_value = "gmail_service"

        result = self.gp.get_gmail_service()
        self.assertEqual(result, "gmail_service")
        mock_flow.assert_called_once()

    def test_msg_mark_modify_add_and_remove(self):
        service = MagicMock()
        messages_mock = service.users().messages()
        modify_mock = messages_mock.modify
        modify_mock.return_value.execute.return_value = {"status": "ok"}

        result = self.gp.msg_mark_modify(service, "msg123", add_labels=["L1"], remove_labels=["L2"])
        self.assertEqual(result, {"status": "ok"})
        modify_mock.assert_called_with(
            userId="me",
            id="msg123",
            body={"addLabelIds": ["L1"], "removeLabelIds": ["L2"]}
        )

    def test_ensure_label_existing(self):
        service = MagicMock()
        service.users().labels().list().execute.return_value = {
            "labels": [{"id": "L1", "name": "Inbox"}, {"id": "L2", "name": "Reports"}]
        }
        result = self.gp.ensure_label(service, "Reports")
        self.assertEqual(result, "L2")

    def test_ensure_label_create_new(self):
        service = MagicMock()
        service.users().labels().list().execute.return_value = {"labels": []}
        service.users().labels().create().execute.return_value = {"id": "NEW_LABEL"}
        result = self.gp.ensure_label(service, "Custom")
        self.assertEqual(result, "NEW_LABEL")

    @patch("core.gmail_service.init_db")
    @patch("core.gmail_service.get_session")
    @patch.object(GmailProcessor, "get_gmail_service")
    def test_fetch_and_store_new_email(self, mock_get_service, mock_get_session, mock_init_db):
        service = MagicMock()
        mock_get_service.return_value = service

        service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg123"}]
        }
        service.users().messages().get().execute.return_value = {
            "id": "msg123",
            "threadId": "t1",
            "snippet": "Hello world",
            "payload": {"headers": [
                {"name": "Subject", "value": "Test Mail"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "you@example.com"},
            ]},
            "internalDate": "1700000000000",
            "labelIds": ["INBOX"]
        }

        fake_session = MagicMock()
        mock_get_session.return_value = fake_session

        self.gp.fetch_and_store("sqlite:///emails.db", max_results=1)

        mock_init_db.assert_called_once()
        fake_session.add.assert_called()
        fake_session.commit.assert_called()

    @patch("core.gmail_service.init_db")
    @patch("core.gmail_service.get_session")
    @patch.object(GmailProcessor, "get_gmail_service")
    def test_fetch_and_store_duplicate_email(self, mock_get_service, mock_get_session, mock_init_db):
        service = MagicMock()
        mock_get_service.return_value = service
        service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg123"}]
        }
        service.users().messages().get().execute.return_value = {
            "id": "msg123",
            "threadId": "t1",
            "snippet": "Duplicate",
            "payload": {"headers": []},
            "internalDate": "1700000000000",
            "labelIds": []
        }

        fake_session = MagicMock()
        fake_session.add.side_effect = Exception("IntegrityError")
        mock_get_session.return_value = fake_session

        with patch("core.gmail_service.IntegrityError", Exception):
            self.gp.fetch_and_store("sqlite:///emails.db", max_results=1)

        fake_session.rollback.assert_called()


if __name__ == "__main__":
    unittest.main()
