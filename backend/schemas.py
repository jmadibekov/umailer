# Ref at
# https://fastapi.tiangolo.com/tutorial/sql-databases/#create-initial-pydantic-models-schemas

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AttachmentBase(BaseModel):
    filepath: str


class AttachmentCreate(AttachmentBase):
    pass


class Attachment(AttachmentBase):
    id: int
    email_id: int

    class Config:
        orm_mode = True


class EmailBase(BaseModel):
    folder_name: str
    uid: int

    email_from: str
    subject: str
    date: datetime


class EmailCreate(EmailBase):
    pass


class Email(EmailBase):
    id: int
    created_at: datetime

    attachments: List[Attachment] = []

    is_processed: bool
    processing_session_id: Optional[int] = None

    class Config:
        orm_mode = True
