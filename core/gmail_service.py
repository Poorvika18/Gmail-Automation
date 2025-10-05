# gmail_service.py
import os
import pickle
import argparse
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from core.model import Email, init_db, get_session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from dateutil import tz

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]  # need modify to mark/move later



class GmailProcessor(object):

    def __init__(self, credentials_file="core/credentials.json", token_file="core/token.pickle"):
        self.CREDENTIALS_FILE = credentials_file
        self.TOKEN_FILE = token_file


    def get_gmail_service(self,):
        creds = None
        if os.path.exists(self.TOKEN_FILE):
            with open(self.TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        service = build("gmail", "v1", credentials=creds)
        return service
    
    def msg_mark_modify(self, service, msg_id, add_labels=None, remove_labels=None):
        body = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels
        return service.users().messages().modify(userId="me", id=msg_id, body=body).execute()

    def iso_from_internal_date(self, ms):
        # Gmail internalDate is milliseconds since epoch in string
        try:
            ms_int = int(ms)
            return datetime.fromtimestamp(ms_int / 1000.0, tz=tz.tzlocal())
        except Exception:
            return None

    def ensure_label(self, service, label_name):
        res = service.users().labels().list(userId="me").execute()
        labels = res.get("labels", [])
        for lbl in labels:
            if lbl["name"].lower() == label_name.lower():
                return lbl["id"]
        body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        created = service.users().labels().create(userId="me", body=body).execute()
        return created["id"]

    def fetch_and_store(self, db_url="sqlite:///emails.db", max_results=1):
        init_db(db_url)
        session = get_session(db_url)
        service = self.get_gmail_service()

        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=max_results).execute()
        messages = results.get("messages", [])
        print(f"Found {len(messages)} messages to fetch")
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = msg.get("payload", {}).get("headers", [])
            header_map = {h["name"].lower(): h["value"] for h in headers}
            subject = header_map.get("subject", "")
            sender = header_map.get("from", "")
            to = header_map.get("to", "")
            snippet = msg.get("snippet", "")
            internal_date = self.iso_from_internal_date(msg.get("internalDate", "0"))
            is_read = "UNREAD" not in msg.get("labelIds", [])
            email = Email(
                message_id=msg["id"],
                thread_id=msg.get("threadId"),
                subject=subject,
                sender=sender,
                to=to,
                snippet=snippet,
                internal_date=internal_date,
                is_read=is_read,
            )
            try:
                session.add(email)
                session.commit()
                print("Stored:", subject)
            except IntegrityError:
                session.rollback()
                print("Already stored:", subject)
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="sqlite:///emails.db")
    parser.add_argument("--max", dest="max_results", type=int, default=100)
    args = parser.parse_args()
    GmailProcessor().fetch_and_store(args.db, args.max_results)
