import os

import pytest
from sqlalchemy import create_engine, text


def make_doris_engine():
    host = os.environ['DORIS_HOST']
    user = os.environ['DORIS_USER']
    password = os.environ['DORIS_PASSWORD']
    port = os.environ['DORIS_PORT']
    database = os.environ['DORIS_DATABASE']
    database = 'doris_test_db'
    tmp_eng = create_engine(f"doris://{user}:{password}@{host}:{port}?charset=utf8mb4")
    with tmp_eng.connect() as c:
        c.execute(text(f'CREATE DATABASE IF NOT EXISTS {database};'))

    engine = create_engine(f"doris://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4", echo=True)

    return engine

@pytest.fixture
def doris_engine():
    return make_doris_engine()