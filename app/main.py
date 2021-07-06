from functools import lru_cache
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException

from . import config
from .handler import Email, EmailServer

app = FastAPI(title="emailer")


@lru_cache()
def get_settings():
    return config.Settings()


@app.get("/")
def read_root():
    return {"msg": "Hello I'm umailer!"}


@app.get("/emails/{uid}", response_model=Email)
def read_email(uid: int, settings: config.Settings = Depends(get_settings)):
    """
    Parameter uid is received, and the respective email is returned.
    """
    try:
        email_server = EmailServer(settings, only_unread=False, is_readonly=True)
        return email_server.read_email(uid)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/emails/download/", response_model=List[Email])
def download_email(
    settings: config.Settings = Depends(get_settings),
    only_unread: bool = True,
    is_readonly: bool = True,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    Parameters date_from and date_to are optionals, but otherwise need to be passed in YYYY-MM-DD format.
    If they're are not passed then the last 30 days will considered as the default interval.
    Emails are searched for interval [date_from, date_to), i.e. date_from is included but not date_to.


    You can set is_readonly to False to be able to alter the inbox (e.g. as read) (default is True).
    """
    try:
        email_server = EmailServer(
            settings, only_unread, is_readonly, date_from, date_to
        )
        return email_server.download_emails()
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
