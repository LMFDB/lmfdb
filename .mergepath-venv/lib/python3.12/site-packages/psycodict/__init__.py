# -*- coding: utf-8 -*-
"""
This module provides an interface to Postgres supporting
the kinds of queries needed by the LMFDB.

The examples in this package's docstrings are real transcripts, run as
doctests by ``tests/test_doctests.py`` against two small tables of LMFDB
data that it creates: ``test_fields`` (22 selected number fields of
degree at most 3) and ``test_curves`` (a dozen elliptic curves over three
of those fields).

EXAMPLES::

    >>> from psycodict.database import PostgresDatabase
    >>> db = PostgresDatabase()  # configuration found via $PSYCODICT_CONFIG / config.ini
    >>> db
    Interface to Postgres database
    >>> 'test_fields' in db.tablenames
    True
    >>> nf = db.test_fields
    >>> nf
    Interface to Postgres table test_fields

You can search using the methods ``search``, ``lucky`` and ``lookup``::

    >>> nf.lookup('2.0.23.1', 'class_number')
    3
    >>> nf.lucky({'degree': 2, 'disc_sign': 1, 'disc_abs': 5}, projection=0)
    '2.2.5.1'
    >>> list(nf.search({'ramps': {'$contains': [2]}}, projection=0))
    ['2.0.4.1', '2.0.8.1', '2.2.8.1', '2.2.12.1', '3.1.44.1', '3.1.76.1']
"""

# Single source of truth for the package version: pyproject.toml reads it via
# ``[tool.setuptools.dynamic]``, and it works from an uninstalled checkout too.
__version__ = "1.0.0rc1"

try:
    import psycopg
    assert psycopg
except ImportError:
    print('Missing psycopg dependency; either do "pip install psycopg[binary]" or "pip install psycopg" (requires libpq installed on your system)')
    raise

from .utils import DelayCommit

assert DelayCommit
# Re-export the SQL composition classes of the driver psycodict is built on.
# Downstream projects that compose queries for _execute should import these
# from psycodict rather than from a driver directly, so that their code does
# not depend on which driver psycodict uses.
from psycopg.sql import SQL, Identifier, Placeholder, Literal, Composable, Composed

assert SQL and Identifier and Placeholder and Literal and Composable and Composed
