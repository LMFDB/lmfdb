"""
A Python interface to the L-functions and modular forms database (LMFDB).

``from lmfdb_client import db`` gives access to the database; see the
README for examples.  Importing this package is cheap: the configuration is
read and the connection made the first time ``db`` is used.
"""

from ._lazy import LazyDatabase

__version__ = "0.1.0"


def _make_database(config=None, **kwargs):
    from .database import LMFDBDatabase
    return LMFDBDatabase(config=config, **kwargs)


db = LazyDatabase(_make_database)

__all__ = ["db", "LazyDatabase"]
