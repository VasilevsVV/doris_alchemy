#! /usr/bin/python3

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from abc import ABC, abstractmethod
import json
import logging
import re
from typing import Callable, Generic, Iterable, Optional, List, Any, Sequence, Type, Dict, TypeVar
from sqlalchemy import Boolean, Dialect, Numeric, Integer, Float, exc
from sqlalchemy.dialects.mysql.base import MySQLTypeCompiler
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql.type_api import TypeEngine
# import sqlalchemy.types as sqltypes

from doris_alchemy.util import ensure_sequence
from doris_alchemy.util import join_args_with_quote

logger = logging.getLogger(__name__)

T = TypeVar('T')

class TINYINT(Integer):  # pylint: disable=no-init
    __visit_name__ = "TINYINT"


class BOOLEAN(Boolean):
    __visit_name__ = "DORIS_BOOLEAN"


class LARGEINT(Integer):  # pylint: disable=no-init
    __visit_name__ = "LARGEINT"


class DOUBLE(Float):  # pylint: disable=no-init
    __visit_name__ = "DOUBLE"


class HLL(Numeric):  # pylint: disable=no-init
    __visit_name__ = "HLL"


class BITMAP(Numeric):  # pylint: disable=no-init
    __visit_name__ = "BITMAP"


class QUANTILE_STATE(Numeric):  # pylint: disable=no-init
    __visit_name__ = "QUANTILE_STATE"

class AGG_STATE(Numeric):  # pylint: disable=no-init
    __visit_name__ = "AGG_STATE"


class BLOB(sqltypes.BLOB):
    __visit_name__ = 'DORIS_BLOB'
    
    def bind_processor(self, dialect):
        return super().bind_processor(dialect)
    
    def result_processor(self, dialect, coltype):
        return super().result_processor(dialect, coltype)


class STRING(sqltypes.Text):
    __visit_name__ = 'DORIS_STRING'
    


class ENUM(sqltypes.Enum):
    __visit_name__ = 'DORIS_ENUM'
    

class ARRAY(sqltypes.ARRAY, Generic[T]):  # pylint: disable=no-init
    __visit_name__ = "DORIS_ARRAY"
    
    def bind_processor(self, dialect: Dialect) -> Callable[[Any], str] | None: # type: ignore
        def __processor(value: list) -> str:
            assert isinstance(value, Iterable), f'ARRAY value must be Iterable. Got: {value}'
            return json.dumps(value)
        return __processor
    
    
    def result_processor(self, dialect: Dialect, coltype: object) -> Callable[[str], list] | None: # type: ignore
        def __processor(value: str):
            res = json.loads(value)
            assert isinstance(res, list)
            return res
        return __processor


class MAP(TypeEngine):  # pylint: disable=no-init
    __visit_name__ = "MAP"

    @TypeEngine.python_type.getter
    def python_type(self) -> Optional[Type[Dict[Any, Any]]]:
        return dict


class STRUCT(TypeEngine):  # pylint: disable=no-init
    __visit_name__ = "STRUCT"

    @TypeEngine.python_type.getter
    def python_type(self) -> Optional[Type[Any]]:
        return None


_type_map = {
    # === Boolean ===
    "boolean": sqltypes.BOOLEAN,
    "bool": sqltypes.BOOLEAN,
    # === Integer ===
    "tinyint": sqltypes.SMALLINT,
    "smallint": sqltypes.SMALLINT,
    "int": sqltypes.INTEGER,
    "bigint": sqltypes.BIGINT,
    "largeint": LARGEINT,
    # === Floating-point ===
    "float": sqltypes.FLOAT,
    "double": DOUBLE,
    # === Fixed-precision ===
    "decimal": sqltypes.DECIMAL,
    "decimalv3": sqltypes.DECIMAL,
    # === String ===
    "varchar": sqltypes.VARCHAR,
    "char": sqltypes.CHAR,
    "json": sqltypes.JSON,
    "jsonb": sqltypes.JSON,
    "text": sqltypes.TEXT,
    "string": sqltypes.String,
    # === Date and time ===
    "date": sqltypes.DATE,
    "datev2": sqltypes.DATE,
    "datetime": sqltypes.DATETIME,
    "datetimev2": sqltypes.DATETIME,
    # === Structural ===
    'array': ARRAY,
    'map': MAP,
    'struct': STRUCT,
    'hll': HLL,
    'quantile_state': QUANTILE_STATE,
    'bitmap': BITMAP,
    'agg_state': AGG_STATE,
}


def parse_sqltype(type_str: str) -> TypeEngine:
    type_str = type_str.strip().lower()
    match = re.match(r"^(?P<type>\w+)\s*(?:\((?P<options>.*)\))?", type_str)
    if not match:
        logger.warning(f"Could not parse type name '{type_str}'")
        return sqltypes.NULLTYPE
    type_name = match.group("type")

    if type_name not in _type_map:
        logger.warning(f"Did not recognize type '{type_name}'")
        return sqltypes.NULLTYPE
    type_class = _type_map[type_name]
    return type_class()


class RenderedMixin(ABC):
    @abstractmethod
    def render(self) -> str:
        pass


class HASH(RenderedMixin):
    def __init__(self, keys: Sequence[str]|str, buckets: Optional[int] = None):
        self.keys: Iterable[str] = ensure_sequence(keys)
        self.buckets = buckets or 'auto'

    def render(self) -> str:
        keys_str = 'HASH' + join_args_with_quote(*self.keys)
        buckets_str = f'BUCKETS {self.buckets}'
        return keys_str + ' ' + buckets_str


class RANGE(RenderedMixin):
    def __init__(self, keys: Sequence[str]|str, part_info: Sequence = tuple()):
        self.keys: Iterable[str] = ensure_sequence(keys)
        self.part_info = ensure_sequence(part_info)

    def render(self) -> str:
        keys_str = 'RANGE' + join_args_with_quote(*self.keys)
        if len(self.part_info) > 0:
            part_str = ',\n    '.join([str(val) for val in self.part_info])
            part_str = '(\n    ' + part_str + '\n)'
        else:
            part_str = '()'
        return keys_str + ' ' + part_str


class RANDOM(RenderedMixin):
    def __init__(self, buckets: Optional[int]=None):
        self.buckets = buckets or 'auto'

    def render(self) -> str:
        keys_str = 'RANDOM'
        keys_str += f' BUCKETS {self.buckets}'
        return keys_str


# ============================================================================
#           TYPE COMPILER

class DorisTypeCompiler(MySQLTypeCompiler):
    def visit_DORIS_BOOLEAN(self, type_, **kw): # type: ignore
        return "BOOLEAN"
    
    def visit_large_binary(self, type_, **kw):
        return self.visit_DORIS_BLOB(type_)
    
    def visit_DORIS_BLOB(self, type_, **kw):
        return "STRING"
    
    def visit_NUMERIC(self, type_, **kw):
        return self.visit_DECIMAL(type_, **kw)

    def _visit_enumerated_values(self, name, type_, enumerated_values: Sequence[str]):
        quoted_enums = []
        for e in enumerated_values:
            if self.dialect.identifier_preparer._double_percents:
                e = e.replace("%", "%%")
            quoted_enums.append("'%s'" % e.replace("'", "''"))

        max_length = 0
        for e in quoted_enums:
            assert isinstance(e, str)
            if len(e) > max_length:
                max_length = len(e)

        if len(enumerated_values) > 0 and max_length > 0:
            return self._extend_string(type_, {}, "VARCHAR(%d)" % max_length)
        else:
            raise exc.CompileError(
                f'ENUM requires more than one Value with length > 0. Got: {enumerated_values}'
            )
    
    def visit_BITMAP(self, type_):
        return 'BITMAP'
    
    def visit_DORIS_ARRAY(self, type_: ARRAY):
        return f'ARRAY <{type_.item_type.compile()}>'
    
    
    def visit_TEXT(self, type_, **kw):
        res = self.visit_DORIS_STRING(type_, **kw)
        print(res)
        return res
    
    def visit_string(self, type_, **kw):
        return self.visit_DORIS_STRING(type_, **kw)
    
    def visit_DORIS_STRING(self, type_: STRING, **kw):
        if type_.length is not None:
            return self._extend_string(type_, {}, "STRING(%d)" % type_.length)
        else:
            return self._extend_string(type_, {}, "STRING")