import logging
from doris_alchemy.const import TABLE_KEY_OPTIONS, TABLE_PROPERTIES_SORT_TUPLES
from doris_alchemy.datatype import HASH, RenderedMixin
from doris_alchemy.dialect import DorisDialectMixin
from doris_alchemy.util import format_properties, join_args_with_quote


from sqlalchemy import Column, Table, exc
from sqlalchemy.dialects.mysql.base import MySQLDDLCompiler
from sqlalchemy.schema import CreateTable, SchemaConst
from sqlalchemy.sql import sqltypes
from sqlalchemy.util import topological


from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)

class DorisDDLCompiler(MySQLDDLCompiler):
    def __init__(self, *args, **kw):
        super(DorisDDLCompiler, self).__init__(*args, **kw)
        self.dialect: DorisDialectMixin


    def visit_create_table(self, create: CreateTable, **kw):
        table: Table = create.element
        preparer = self.preparer

        text = "\nCREATE "
        if table._prefixes:
            text += " ".join(table._prefixes) + " "

        text += "TABLE "
        if create.if_not_exists:
            text += "IF NOT EXISTS "

        text += preparer.format_table(table) + " "

        create_table_suffix = self.create_table_suffix(table)
        if create_table_suffix:
            text += create_table_suffix + " "

        text += "("

        separator = "\n"

        # if only one primary key, specify it along with the column
        # first_pk = False primary key is not supported
        for create_column in create.columns:
            column = create_column.element
            # assert column.primary_key is False
            try:
                processed = self.process(create_column)
                if processed is not None:
                    text += separator
                    separator = ", \n"
                    text += "\t" + processed
                # if column.primary_key:
                #     first_pk = True
            except exc.CompileError as ce:
                raise exc.CompileError(
                    "(in table '%s', column '%s'): %s"
                    % (table.description, column.name, ce.args[0])
                ) from ce

        text += "\n)\n%s\n\n" % self.post_create_table(table)
        return text



    def __compile_table_arg(self, option: str, arg: Any, table_name: str) -> Optional[str]:
        option = option.replace("_", " ")
        # if option in _reflection._options_of_type_string:
        if option == 'COMMENT':
            arg = self.sql_compiler.render_literal_value(arg, sqltypes.String())
            return f'{option} {arg}'
        if option in TABLE_KEY_OPTIONS:
            if isinstance(arg, str):
                return '{} {}'.format(option, join_args_with_quote(arg))
            else:
                assert isinstance(arg, Sequence)
                return '{} {}'.format(option, join_args_with_quote(*arg))
        if option in ['PARTITION BY', 'DISTRIBUTED BY']:
            assert isinstance(arg, RenderedMixin)
            return '{} {}'.format(option, arg.render())
        if option == 'PROPERTIES':
            assert isinstance(arg, dict)
            return '{} {}'.format(option, format_properties(**arg))
        if option == 'ENGINE':
            assert isinstance(arg, str)
            return f'{option} {arg}'
        return None


    def post_create_table(self, table: Table):
        "Builds top level CREATE TABLE options, like ENGINE and COLLATE."

        table_opts = []
        opts = {}
        for k, v in table.kwargs.items():
            if k.startswith("%s_" % self.dialect.name):
                opts[k[len(self.dialect.name) + 1:].upper()] = v
        if table.comment is not None:
            opts["COMMENT"] = table.comment
        pk = table.primary_key
        if opts.get('AUTOGEN_PRIMARY_KEY', False) and len(pk) > 0:
            pk_key = tuple(c.name for c in pk)
            if 'UNIQUE_KEY' not in opts:
                opts['UNIQUE_KEY'] = pk_key
            if 'DISTRIBUTED_BY' not in opts:
                opts['DISTRIBUTED_BY'] = HASH(pk_key)


        sorted_opts = topological.sort(TABLE_PROPERTIES_SORT_TUPLES, opts)
        for opt in sorted_opts:
            __arg = opts[opt]
            __compiled = self.__compile_table_arg(opt, __arg, table.name)
            if __compiled:
                table_opts.append(__compiled)
        text = "\n".join(table_opts)
        return text

    def visit_create_column(self, create, first_pk=False, **kw):
        column = create.element
        if column.system:
            return None
        text = self.get_column_specification(column, first_pk=first_pk)
        const = " ".join(
            self.process(constraint) for constraint in column.constraints
        )
        if const:
            text += " " + const
        return text

    def get_column_specification(self, column: Column, **kw):
        """Builds column DDL."""
        if (
            self.dialect.is_mariadb is True
            and column.computed is not None
            and column._user_defined_nullable is SchemaConst.NULL_UNSPECIFIED
        ):
            column.nullable = True
        colspec = [
            self.preparer.format_column(column),
            self.dialect.type_compiler_instance.process(
                column.type, type_expression=column
            ),
        ]

        if column.computed is not None:
            colspec.append(self.process(column.computed))

        is_timestamp = isinstance(
            column.type._unwrapped_dialect_impl(self.dialect),
            sqltypes.TIMESTAMP,
        )

        if not column.nullable:
            colspec.append("NOT NULL")

        # see: https://docs.sqlalchemy.org/en/latest/dialects/mysql.html#mysql_timestamp_null  # noqa
        elif column.nullable and is_timestamp:
            colspec.append("NULL")

        comment = column.comment
        if comment is not None:
            literal = self.sql_compiler.render_literal_value(
                comment, sqltypes.String()
            )
            colspec.append("COMMENT " + literal)

        else:
            default = self.get_column_default_string(column)
            if default is not None:
                colspec.append("DEFAULT " + default)
        return " ".join(colspec)