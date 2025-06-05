from sqlalchemy import create_engine
from urllib.parse import quote
import os


username=os.environ.get('DB_USER')
password=os.environ.get('DB_PASS')
host=os.environ.get('DB_HOST')

engine = create_engine(f'postgresql://{quote(username)}:{quote(password)}@{host}:5432/poolaccounts_dummy')

