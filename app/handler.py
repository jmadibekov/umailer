import email
import os
import re
import unicodedata
from datetime import datetime, time, timedelta
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from random import randint
from typing import List

import pytz
from imapclient import SEEN, IMAPClient
from pydantic import BaseModel

from .config import Settings


class Email(BaseModel):
    uid: int
    email_from: str
    subject: str
    date: datetime
    attachment_paths: List[str]


class EmailServer:
    def __init__(
        self,
        settings: Settings,
        only_unread: bool = True,
        is_readonly: bool = True,
        date_from: str = None,
        date_to: str = None,
    ) -> None:
        self.settings = settings
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

    def read_email(self, uid: int) -> Email:
        with IMAPClient(self.settings.email_host) as client:
            client.login(self.settings.email_username, self.settings.email_password)
            client.select_folder("INBOX", readonly=self.is_readonly)

            message_data = client.fetch([uid], "RFC822")[uid]

            email_message = email.message_from_bytes(
                message_data[b"RFC822"], policy=policy.default
            )

            _, email_address = parseaddr(email_message.get("From"))
            subject = email_message.get("Subject")
            email_datetime = parsedate_to_datetime(email_message.get("Date"))

            return Email(
                uid=uid,
                email_from=email_address,
                subject=subject,
                date=email_datetime,
                attachment_paths=[],
            )

    def save_attachment(self, uid: int, email_message: EmailMessage) -> Email:
        attachment_paths = []
        _, email_address = parseaddr(email_message.get("From"))
        subject = email_message.get("Subject")
        email_datetime = parsedate_to_datetime(email_message.get("Date"))

        # iterate over email parts
        for part in email_message.walk():
            content_maintype = part.get_content_maintype()
            content_disposition = part.get("Content-Disposition")

            if content_maintype == "multipart" or content_disposition is None:
                continue

            filename = part.get_filename()

            root, ext = os.path.splitext(filename)
            filename = f"{email_address}_{self.random_with_n_digits(6)}_{self.slugify(root, allow_unicode=True)}{ext}"

            attachment_path = os.path.join(
                self.settings.path_to_download_attachments, filename
            )

            # download attachment and save it
            attachment_data = part.get_payload(decode=True)
            with open(attachment_path, mode="wb") as writer:
                # note that .txt files sent from <mailer@osmp.kz> uses 'cp1251' encoding
                writer.write(attachment_data)

            attachment_paths.append(attachment_path)

        email_object = Email(
            uid=uid,
            email_from=email_address,
            subject=subject,
            date=email_datetime,
            attachment_paths=attachment_paths,
        )

        return email_object

    def download_emails(self) -> List[Email]:
        saved_emails = []
        with IMAPClient(self.settings.email_host) as client:
            client.login(self.settings.email_username, self.settings.email_password)
            client.select_folder("INBOX", readonly=self.is_readonly)

            criteria = []
            if self.only_unread:
                criteria.append("UNSEEN")

            criteria.extend(
                ["SINCE", self.date_from.date(), "BEFORE", self.date_to.date()]
            )

            emails = client.search(criteria)

            for uid, message_data in client.fetch(emails, "RFC822").items():
                # parse email from bytes to EmailMessage object
                email_message = email.message_from_bytes(
                    message_data[b"RFC822"], policy=policy.default
                )

                saved_emails.append(self.save_attachment(uid, email_message))

            if not self.is_readonly:
                # fetching emails already marks them as read, but the following
                # line makes it explicit for readers
                client.add_flags(emails, [SEEN])

        return saved_emails
