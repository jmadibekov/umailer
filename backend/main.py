from functools import lru_cache
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from imapclient import IMAPClient
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import config, crud, models, schemas
from .database import SessionLocal, engine
from .handler import EmailServer

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="umailer")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@lru_cache()
def get_settings():
    return config.Settings()


@app.get("/")
def read_root():
    return {"msg": "Hello, I'm umailer!"}


class Response(BaseModel):
    number_of_newly_downloaded_emails: int
    emails: List[schemas.Email]


# Do note that there's no trailing slash by design (not /emails/download/ but /emails/download).
# However, in most cases, you don't even need to worry about it because FastAPI succesfully redirects
# your request with a trailing slash to without (e.g. /emails/download/ to /emails/download).
#
# Why I chose to design it without trailing slash is because:
# - https://github.com/tiangolo/fastapi/issues/51#issuecomment-491364756
#
@app.post("/emails/download", response_model=Response)
def download_email(
    only_unread: bool = True,
    is_readonly: bool = True,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    settings: config.Settings = Depends(get_settings),
    db: Session = Depends(get_db),
):
    """
    Parameters [date_from] and [date_to] are optionals, but otherwise need to be passed in YYYY-MM-DD format.
    Note that emails are searched for interval [date_from, date_to] (both date_from and date_to are included).

    If they're are not passed (both or either of them), then the last 30 days will considered as the default interval.

    You can set [is_readonly] to False to be able to alter the inbox (i.e. mark the emails as READ).
    When [is_readonly] is True (which is default) email inbox isn't affected at all.
    """
    # TODO: Add logs to the stdout while emails are being read and downloaded, and make following asynchronous
    # TODO: it has unintended consequence of marking emails as READ that are not within the given interval.
    try:
        email_server = EmailServer(
            settings, db, only_unread, is_readonly, date_from, date_to
        )
        emails = email_server.download_emails()
        return Response(
            number_of_newly_downloaded_emails=email_server.number_of_newly_downloaded_emails,
            emails=emails,
        )

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/emails/download-by-uid", response_model=Response)
def download_by_uid(
    uid: int,
    settings: config.Settings = Depends(get_settings),
    db: Session = Depends(get_db),
):
    """
    Parameter uid is received, and respective email with such UID downloaded, saved and returned.

    Note that this request doesn't have capability to mark the email as SEEN or read
    (i.e. [is_readonly] is always True).
    """
    try:
        email_server = EmailServer(settings, db, only_unread=False, is_readonly=True)
        email = email_server.download_emails(uid)

        return Response(
            number_of_newly_downloaded_emails=email_server.number_of_newly_downloaded_emails,
            emails=email,
        )

    except IMAPClient.Error as error:
        msg = (
            f"IMAP service failed to fetch the email with UID {uid} from inbox. Maybe there's no such email? "
            f"For reference, error = "
            f"{error}"
        )

        raise HTTPException(
            status_code=400,
            detail=msg,
        )


@app.get("/emails/{email_id}", response_model=schemas.Email)
def read_email(email_id: int, db: Session = Depends(get_db)):
    """
    Fetchs email data from database by 'email_id'.

    Note that this endpoint doesn't download email via IMAP, but rather just fetches already-downloaded
    emails from PostgreSQL database.
    """
    db_email = crud.get_email(db, email_id=email_id)
    if db_email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return db_email
