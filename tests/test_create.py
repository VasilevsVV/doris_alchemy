import os
import pytest

import sqlalchemy as sa
from sqlalchemy import create_engine, text

from doris_alchemy import datatype
from doris_alchemy.datatype import RANGE
from doris_alchemy.datatype import HASH
from tests.fixtures import doris_engine


def test_create_table(doris_engine):
    metadata_obj = sa.MetaData()
    table_obj = sa.Table(
        'test_table',
        metadata_obj,
        sa.Column("id", datatype.Integer),
        doris_unique_key=('id', ),
        doris_partition_by=RANGE('id'),
        doris_distributed_by=HASH('id'),
        doris_properties={"replication_allocation": "tag.location.default: 1"}
    )

    metadata_obj.create_all(doris_engine)

    metadata_obj.drop_all(doris_engine, [table_obj])


if __name__ == '__main__':
    host = os.environ['DORIS_HOST']
    user = os.environ['DORIS_USER']
    password = os.environ['DORIS_PASSWORD']
    port = os.environ['DORIS_PORT']
    # engstr = f"doris://{user}:{password}@{host}:{port}?charset=utf8mb4"
    # print(engstr)
    # eng = create_engine(engstr)
    # database = 'doris_test_db'
    # tmp_eng = create_engine(f"doris://{user}:{password}@{host}:{port}?charset=utf8mb4")
    # with tmp_eng.connect() as c:
    #     c.execute(text(f'CREATE DATABASE IF NOT EXISTS {database};'))
    