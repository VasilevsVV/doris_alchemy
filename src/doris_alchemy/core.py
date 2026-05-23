from sqlalchemy.dialects.mysql.mysqldb import MySQLDialect_mysqldb
from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql

from doris_alchemy.datatype import DorisTypeCompiler
from doris_alchemy.ddl import DorisDDLCompiler
from doris_alchemy.dialect import DorisDialectMixin


class DorisDialect_pymysql(DorisDialectMixin, MySQLDialect_pymysql): # type: ignore
    supports_statement_cache = False
    ddl_compiler = DorisDDLCompiler
    type_compiler_cls = DorisTypeCompiler


class DorisDialect_mysqldb(DorisDialectMixin, MySQLDialect_mysqldb): # type: ignore
    supports_statement_cache = False
    ddl_compiler = DorisDDLCompiler
    type_compiler_cls = DorisTypeCompiler


try:
    # using pymysql as default driver if available
    DorisDialect = DorisDialect_pymysql
    

except ModuleNotFoundError:
    DorisDialect = DorisDialect_mysqldb
