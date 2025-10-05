# import sqlite3

# class EmailModel:
#     def __init__(self, db_name="emails.db"):
#         self.db_name = db_name
#         self.conn = None
#         self.cursor = None
#         self._connect()
#         self._create_table()

#     def _connect(self):
#         """Connect to SQLite database."""
#         try:
#             self.conn = sqlite3.connect(self.db_name)
#             self.cursor = self.conn.cursor()
#         except sqlite3.Error as e:
#             print(f"Error connecting to database: {e}")

#     def _create_table(self):
#         """Creates the 'emails' table if it doesn't exist."""
#         if self.cursor:
#             self.cursor.execute('''
#                 CREATE TABLE IF NOT EXISTS emails (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     gmail_id TEXT NOT NULL UNIQUE, -- Gmail message id
#                     thread_id TEXT,
#                     sender TEXT,
#                     recipient TEXT,
#                     subject TEXT,
#                     snippet TEXT,
#                     received_datetime TEXT,
#                     is_read INTEGER DEFAULT 0
#                 )
#             ''')
#             self.conn.commit()

#     def insert_email(self, gmail_id, thread_id, sender, recipient, subject, snippet, received_datetime, is_read=0):
#         """Insert a new email record."""
#         try:
#             self.cursor.execute('''
#                 INSERT INTO emails (gmail_id, thread_id, sender, recipient, subject, snippet, received_datetime, is_read)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#             ''', (gmail_id, thread_id, sender, recipient, subject, snippet, received_datetime, is_read))
#             self.conn.commit()
#         except sqlite3.IntegrityError:
#             print(f"Email with Gmail ID '{gmail_id}' already exists.")
#         except sqlite3.Error as e:
#             print(f"Error inserting email: {e}")

#     def get_all_emails(self):
#         """Fetch all stored emails."""
#         self.cursor.execute("SELECT * FROM emails")
#         return self.cursor.fetchall()

#     def get_unread_emails(self):
#         """Fetch unread emails."""
#         self.cursor.execute("SELECT * FROM emails WHERE is_read = 0")
#         return self.cursor.fetchall()

#     def mark_as_read(self, gmail_id):
#         """Update email as read."""
#         self.cursor.execute("UPDATE emails SET is_read = 1 WHERE gmail_id = ?", (gmail_id,))
#         self.conn.commit()

#     def delete_email(self, gmail_id):
#         """Delete email by Gmail ID."""
#         self.cursor.execute("DELETE FROM emails WHERE gmail_id = ?", (gmail_id,))
#         self.conn.commit()

#     def close(self):
#         if self.conn:
#             self.conn.close()



# models.py
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Email(Base):
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True)
    message_id = Column(String, unique=True, index=True)  # Gmail message id
    thread_id = Column(String, index=True)
    subject = Column(String)
    sender = Column(String)
    to = Column(String)
    snippet = Column(Text)
    internal_date = Column(DateTime)  # when received
    is_read = Column(Boolean, default=False)

def get_engine(db_url="sqlite:///emails.db"):
    return create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})

def get_session(db_url="sqlite:///emails.db"):
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()

def init_db(db_url="sqlite:///emails.db"):
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
