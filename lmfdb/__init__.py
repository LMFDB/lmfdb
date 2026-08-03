"""
LMFDB: the database of L-functions, modular forms, and related objects.

Importing this package is lightweight; in particular it does not connect
to the database.  ``lmfdb.db`` is a lazy proxy: the connection is
established the first time it is used, for example::

    from lmfdb import db
    db.ec_curvedata.lookup("11.a1")

or explicitly via ``db.connect()``.  To run the website, use the ``lmfdb``
command (or ``python -m lmfdb``, or ``start-lmfdb.py`` from a git checkout).
"""

from ._lazy_database import db

__all__ = ["db"]
