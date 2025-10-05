# process_rules.py
import argparse
import json
import os
import pickle
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from core.model import get_session, Email
from sqlalchemy import or_
from googleapiclient.errors import HttpError
from core.gmail_service import GmailProcessor

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "google_credentials.json"

class RuleProcessor(object):
    def __init__(self):
        self.gmail_service = GmailProcessor()
        self.field_mapping = {
            ("from", "sender"): "sender",
            ("subject",): "subject",
            ("message", "snippet", "body"): "snippet",
            ("received", "received date", "received date/time", "internal_date"): "internal_date"
        }

        self.condition_rule_map = {
            "contains": lambda target, val: val in target,
            "does not contain": lambda target, val: val not in target,
            "equals": lambda target, val: target == val,
            "does not equal": lambda target, val: target != val
        }

        self.predicate_aliases = {
            "contains": "contains",
            "not contains": "does not contain", 
            "does not contain": "does not contain",
            "equals": "equals",
            "equal": "equals",
            "does not equal": "does not equal",
            "not equal": "does not equal"
        }

        self.date_rule_map = {
            "less_than_days": lambda target, val: target > (datetime.now(target.tzinfo) - timedelta(days=int(val))),
            "greater_than_days": lambda target, val: target < (datetime.now(target.tzinfo) - timedelta(days=int(val))),
            "less_than": lambda target, val: target < dateparser.parse(val),
            "greater_than": lambda target, val: target > dateparser.parse(val),
        }

        self.date_predicate_aliases = {
            "lt_days": "less_than_days",
            "less_than_days": "less_than_days",
            "gt_days": "greater_than_days",
            "greater_than_days": "greater_than_days",
            "lt": "less_than",
            "less_than": "less_than",
            "gt": "greater_than",
            "greater_than": "greater_than",
        }

    def get_field_value(self, email_obj, field_name):
        for keys, attr in self.field_mapping.items():
            if field_name.lower() in [k.lower() for k in keys]:
                return getattr(email_obj, attr, "")  # safely get attribute
        return ""


    def evaluate_condition(self, email_obj, cond):
        field = cond["field"].lower()
        pred = cond["predicate"].lower()
        val = cond.get("value")
        # string fields: From, Subject, Message
        target = self.get_field_value(email_obj, field)
        # string preds
        if field in ("from", "subject", "message", "snippet", "body", "sender"):
                val_s = (val or "").lower()
                target_s = (target or "").lower()
                pred_key = self.predicate_aliases.get(pred.lower())
                if not pred_key:
                    return False
                func = self.condition_rule_map[pred_key]
                return func(target_s, val_s)
        
        # date preds: val expected to be integer days or ISO date depending on predicate
        if field == "internal_date":
            if not isinstance(target, datetime):
                return False
            pred_key = self.date_predicate_aliases.get(pred.lower())
            
            if not pred_key:
                return False
            func = self.date_rule_map[pred_key]
            return func(target, val)
        
        return False

    def run_rules(self, db_url, rules_path):
        service = GmailProcessor().get_gmail_service()
        session = get_session(db_url)
        with open(rules_path, "r") as f:
            rules_data = json.load(f)

        # rules_data expected to be a list of rules or object with "rules" key
        rules = rules_data.get("rules") if "rules" in rules_data else rules_data
        for rule in rules:
            name = rule.get("name", "<unnamed>")
            conditions = rule.get("conditions", [])
            predicate = rule.get("predicate", "All").lower()  # All / Any per rule (default All)
            actions = rule.get("actions", [])

            print(f"Applying rule: {name} ({predicate})")

            # naive evaluate: fetch all emails and filter in python (could be optimized)
            emails = session.query(Email).all()
            matches = []
            for e in emails:
                results = [self.evaluate_condition(e, c) for c in conditions]
                match = all(results) if predicate == "all" else any(results)
                if match:
                    matches.append(e)
            print(f"  {len(matches)} matches")

            for e in matches:
                for act in actions:
                    action_name = act.get("action")
                    try:
                        if action_name == "mark_as_read" and not e.is_read:
                            # remove UNREAD label (Gmail uses 'UNREAD' system label)
                            self.gmail_service.msg_mark_modify(service, e.message_id, remove_labels=["UNREAD"])
                            e.is_read = True
                            session.commit()
                            print(f"Marked read: {e.subject}")
                        elif action_name == "mark_as_unread" and e.is_read:
                            self.gmail_service.msg_mark_modify(service, e.message_id, add_labels=["UNREAD"])
                            e.is_read = False
                            session.commit()
                            print(f"Marked unread: {e.subject}")
                        elif action_name == "move_to_label":
                            label_name = act.get("label")
                            if not label_name:
                                print(" No label specified for move_to_label; skipping.")
                                continue
                            label_id = GmailProcessor().ensure_label(service, label_name)
                            self.gmail_service.msg_mark_modify(service, e.message_id, add_labels=[label_id], remove_labels=["INBOX"])
                            print(f"Moved message to {label_name}")
                        else:
                            print("Unknown action:", action_name)
                    except HttpError as err:
                        print("Gmail API error:", err)
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="sqlite:///emails.db")
    parser.add_argument("--rules", default="core/rules.json")
    args = parser.parse_args()
    RuleProcessor().run_rules(args.db, args.rules)
