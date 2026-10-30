"""
The L-functions and Modular Forms Database (https://www.lmfdb.org).

``from lmfdb import db`` gives access to the database, and the ``lmfdb``
command runs the website; see GettingStarted.md.
"""

from ._lazy_database import db

__all__ = ["db"]
