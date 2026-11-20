# -*- coding: utf-8 -*-
"""
SQL composition classes and exception types that track the driver psycodict
is built on.

psycodict is switching from psycopg2 to psycopg3 (roed314/psycodict#88).
Query fragments composed here are executed by psycodict's ``_execute``, so
they must come from the *same* driver psycodict uses -- and both drivers may
be installed at once, so trying imports is not a valid probe.  Instead we key
off psycodict's own re-exported ``SQL``.

Once the psycodict requirement is pinned to a psycopg3-based release, the sql
classes can be imported from psycodict itself (which re-exports them) and the
exceptions from ``psycopg``/``psycopg.errors``, and this module can be
deleted.
"""

import psycodict

if psycodict.SQL.__module__.startswith("psycopg2"):
    from psycopg2 import DatabaseError, DataError
    from psycopg2.errors import NumericValueOutOfRange
    from psycopg2.extensions import QueryCanceledError
    from psycopg2.sql import SQL, Composable, Composed, Identifier, Literal, Placeholder
else:
    from psycopg import DatabaseError, DataError
    from psycopg.errors import NumericValueOutOfRange
    from psycopg.errors import QueryCanceled as QueryCanceledError
    from psycopg.sql import SQL, Composable, Composed, Identifier, Literal, Placeholder

__all__ = [
    "SQL",
    "Composable",
    "Composed",
    "Identifier",
    "Literal",
    "Placeholder",
    "DatabaseError",
    "DataError",
    "NumericValueOutOfRange",
    "QueryCanceledError",
]
