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
