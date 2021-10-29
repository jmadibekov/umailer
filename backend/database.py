# Use this tutorial for reference:
# https://fastapi.tiangolo.com/tutorial/sql-databases/

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# See ref at https://saurabh-kumar.com/python-dotenv/#getting-started
load_dotenv()

DEFAULT_HOST = os.getenv("DEFAULT_HOST")
DEFAULT_PORT = os.getenv("DEFAULT_PORT")
DEFAULT_USER = os.getenv("DEFAULT_USER")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")
DEFAULT_DB = os.getenv("DEFAULT_DB")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DEFAULT_USER}:{DEFAULT_PASSWORD}@{DEFAULT_HOST}/{DEFAULT_DB}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
