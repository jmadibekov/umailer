import email
import os
import re
import unicodedata
from datetime import datetime, time, timedelta
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from random import randint
from typing import List, Optional

import pytz
from imapclient import SEEN, IMAPClient
from sqlalchemy.orm import Session

from . import crud, schemas
from .config import Settings


class EmailServer:
    """
    'folder_name' (default is INBOX) is the folder (aka mailbox) selected to fetch emails.
    """

    def __init__(
        self,
        settings: Settings,
        db: Session,
        only_unread: bool = True,
        is_readonly: bool = True,
        date_from: str = None,
        date_to: str = None,
        folder_name: str = "INBOX",
    ) -> None:
        self.settings = settings
        self.db = db
        self.folder_name = folder_name
        self.number_of_newly_downloaded_emails = 0

        self.only_unread = only_unread
        self.is_readonly = is_readonly

        DATE_FORMAT = "%Y-%m-%d"
        DATE_INTERVAL = 30

        if not date_from or not date_to:
            self.date_from = datetime.combine(
                datetime.now() - timedelta(days=DATE_INTERVAL), time.min
            )
            self.date_to = datetime.combine(
                datetime.now() + timedelta(days=1), time.max
            )

        else:
            self.date_from = datetime.combine(
                datetime.strptime(date_from, DATE_FORMAT), time.min
            )
            self.date_to = datetime.combine(
                datetime.strptime(date_to, DATE_FORMAT), time.max
            )

        almaty_timezone = pytz.timezone("Asia/Almaty")
        self.date_from = almaty_timezone.localize(self.date_from)
        self.date_to = almaty_timezone.localize(self.date_to)

    @staticmethod
    def slugify(value, allow_unicode=False):
        """
        Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
        Remove characters that aren't alphanumerics, underscores, or hyphens.
        Convert to lowercase. Also strip leading and trailing whitespace.
        """
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize("NFKC", value)
        else:
            value = (
                unicodedata.normalize("NFKD", value)
                .encode("ascii", "ignore")
                .decode("ascii")
            )
        value = re.sub(r"[^\w\s-]", "", value).strip().lower()
        return re.sub(r"[-\s]+", "-", value)

    @staticmethod
    def random_with_n_digits(n):
        return "".join(["{}".format(randint(0, 9)) for num in range(0, n)])

    def save_email(
        self, uid: int, email_message: EmailMessage, validate_date: bool
    ) -> Optional[schemas.Email]:
        """
        Might return None if 'validate_date' is True and the email is not within the given interval.
        """
        _, email_address = parseaddr(email_message.get("From"))
        subject = email_message.get("Subject")
        email_datetime = parsedate_to_datetime(email_message.get("Date"))

        if validate_date and not (self.date_from <= email_datetime <= self.date_to):
            # if email date is not within the interval, return None
            return None

        # checking if such email already exists in database (has been downloaded already before)
        db_email = crud.get_email_by_uid(self.db, folder_name=self.folder_name, uid=uid)
        if db_email:
            # then don't bother re-downloading and re-saving attachments
            return db_email

        attachments = []

        # iterate over email parts
        for part in email_message.walk():
            content_maintype = part.get_content_maintype()
            content_disposition = part.get("Content-Disposition")

            if (
                content_maintype == "multipart"
                # to skip logo's in emails or some other unrelated 'png' or 'jpeg' files
                or content_maintype == "image"
                or content_disposition is None
            ):
                continue

            filename = part.get_filename()

            root, ext = os.path.splitext(filename)

            # filename would in format '{datetime}_{folder}_{uid}_{slugified_title}
            filename = (
                f"{email_datetime.isoformat()}_{self.folder_name}_{uid}_"
                f"{self.slugify(root, allow_unicode=True)}{ext}"
            )
            filepath = (
                Path(self.settings.path_to_download_attachments)
                / email_address
                / filename
            )

            # creating folders in case not exist
            filepath.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            # download attachment and save it
            attachment_data = part.get_payload(decode=True)
            with filepath.open(mode="wb") as writer:
                # note that .txt files sent from <mailer@osmp.kz> uses 'cp1251' encoding
                writer.write(attachment_data)

            attachments.append(schemas.AttachmentCreate(filepath=str(filepath)))

        email_object = schemas.EmailCreate(
            folder_name=self.folder_name,
            uid=uid,
            email_from=email_address,
            subject=subject,
            date=email_datetime,
        )

        # at this point, it doesn't exist yet in db, so save it in database
        db_email = crud.create_email(self.db, email_object)
        self.number_of_newly_downloaded_emails += 1
        # TODO: if there's more than one attachment in an email, log warning
        for attachment in attachments:
            crud.create_email_attachment(self.db, attachment, db_email.id)

        return db_email

    def download_emails(self, uid: int = None) -> List[schemas.Email]:
        """
        If 'uid' is received, it will download only that email with that specific uid.
        """
        saved_emails = []

        # 'use_uid' and 'ssl' are True by default
        with IMAPClient(self.settings.email_host) as client:
            client.login(self.settings.email_username, self.settings.email_password)
            client.select_folder(folder=self.folder_name, readonly=self.is_readonly)

            if uid is not None:
                fetcher = client.fetch([uid], "RFC822")
                validate_date = False
            else:
                criteria = []
                if self.only_unread:
                    criteria.append("UNSEEN")

                # IMAP's SINCE and BEFORE interval works really weird,
                # so I just take a few days of offset, then just validate
                # that the date of the email is within the interval
                criteria.extend(
                    [
                        "SINCE",
                        self.date_from.date() - timedelta(days=3),
                        "BEFORE",
                        self.date_to.date() + timedelta(days=3),
                    ]
                )
                validate_date = True

                emails = client.search(criteria)

                fetcher = client.fetch(emails, "RFC822")

            for uid, message_data in fetcher.items():
                # parse email from bytes to EmailMessage object
                email_message = email.message_from_bytes(
                    message_data[b"RFC822"], policy=policy.default
                )

                saved_email = self.save_email(uid, email_message, validate_date)

                if saved_email:
                    saved_emails.append(saved_email)

            if not self.is_readonly:
                # fetching emails already marks them as read, but the following
                # line makes it explicit for readers
                client.add_flags(emails, [SEEN])

        return saved_emails
