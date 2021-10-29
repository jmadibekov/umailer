import os
from pathlib import Path

from pydantic import BaseSettings


def get_and_create_default_directory():
    # absolute_current_dir is .../app
    if os.getenv("PATH_TO_DOWNLOAD_ATTACHMENTS"):
        return os.getenv("PATH_TO_DOWNLOAD_ATTACHMENTS")
    else:
        absolute_current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        path_to_download_attachments = os.path.join(
            absolute_current_dir.parent.absolute(), "attachments"
        )
        os.makedirs(path_to_download_attachments, exist_ok=True)
        return path_to_download_attachments


class Settings(BaseSettings):
    email_host: str = "imap.yandex.com"
    email_username: str
    email_password: str
    path_to_download_attachments: str = get_and_create_default_directory()

    class Config:
        env_file = ".env"
