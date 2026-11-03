"""
The L-functions and Modular Forms Database (https://www.lmfdb.org).

``from lmfdb import db`` gives access to the database, with the website's
configuration, and ``sage -python start-lmfdb.py`` runs the website; see
GettingStarted.md.  Code that only needs the database can use lmfdb-client
instead (``from lmfdb_client import db``), which works without Sage.
"""

from lmfdb_client import LazyDatabase
from lmfdb_utils.site import set_current_site

from .site import LMFDBSite

# Describe the LMFDB to lmfdb-utils (knowls, completeness, ...)
set_current_site(LMFDBSite())


def _make_database(config=None, **kwargs):
    from .lmfdb_database import LMFDBDatabase
    return LMFDBDatabase(config=config, **kwargs)


# Nothing is imported, read or connected until the database is first used
db = LazyDatabase(_make_database)

__all__ = ["db"]
