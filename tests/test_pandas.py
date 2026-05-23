import os
import pandas as pd
import pytest

import sqlalchemy as sa
from sqlalchemy import create_engine, text

from doris_alchemy import datatype
from doris_alchemy.datatype import RANGE
from doris_alchemy.datatype import HASH
from tests.fixtures import doris_engine, make_doris_engine


def test_pandas_df_to_sql_1(doris_engine):
    df = pd.DataFrame({
        'foo': [1,2,3],
        'bar': ['a', 'b', 'c']
    })
    df.to_sql('test_pandas_table', doris_engine, index=False, if_exists='replace')


def test_pandas_to_sql_2(doris_engine):
    df = pd.DataFrame({
        'foo': [1,2,3],
        'bar': ['a', 'b', 'c'],
        'floatie': [1., 2., 3.]
    })
    df.to_sql('test_pandas_table', doris_engine, index=False, if_exists='replace')



# if __name__ == '__main__':
#     eng = make_doris_engine()
#     df = pd.DataFrame({
#         'foo': [1,2,3],
#         'bar': ['a', 'b', 'c'],
#         'floatie': [1., 2., 3.]
#     })
#     df.to_sql('test_pandas_table', eng, index=False, if_exists='replace')
