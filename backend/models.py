import os
from datetime import datetime

import pytz
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import Boolean, DateTime

from .database import Base

load_dotenv()

prefix = os.getenv("TABLE_NAME_PREFIX")
if prefix:
    prefix = f"{prefix}_"
else:
    prefix = ""


def current_time_with_timezone():
    almaty_timezone = pytz.timezone("Asia/Almaty")
    return almaty_timezone.localize(datetime.now())


# TODO: possibly add migrations support in the future
class Email(Base):
    __tablename__ = f"{prefix}emails"

    # On UniqueConstraint see at
    # https://stackoverflow.com/questions/10059345/sqlalchemy-unique-across-multiple-columns
    __table_args__ = (UniqueConstraint("folder_name", "uid"),)

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # all UID-s in each folder are unique (2 messages in different folders may have same UID)
    # see more at
    # https://stackoverflow.com/questions/2543534/how-to-determine-the-uid-of-a-message-in-imap
    # and at
    # https://www.limilabs.com/blog/unique-id-in-imap-protocol
    folder_name = Column(String, index=True)
    uid = Column(Integer, index=True)

    email_from = Column(String, index=True)
    subject = Column(String)
    date = Column(DateTime(timezone=True), index=True)

    attachments = relationship("Attachment", back_populates="email")

    is_processed = Column(Boolean, default=False)
    processing_session_id = Column(Integer, nullable=True)


class Attachment(Base):
    __tablename__ = f"{prefix}attachments"

    id = Column(Integer, primary_key=True, index=True)
    filepath = Column(String, unique=True, index=True)

    email_id = Column(Integer, ForeignKey(f"{prefix}emails.id"))

    email = relationship("Email", back_populates="attachments")
