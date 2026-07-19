"""
LMFDB: the database of L-functions, modular forms, and related objects.

Importing this package is lightweight; in particular it does not connect
to the database.  The connection is established the first time ``lmfdb.db``
is used, for example::

    from lmfdb import db
    db.ec_curvedata.lookup("11.a1")

or explicitly via ``db.connect()``.  To run the website, use the ``lmfdb``
command (or ``python -m lmfdb``, or ``start-lmfdb.py`` from a git checkout).
"""


def __getattr__(name):
    # Lazy attributes (PEP 562), so that `import lmfdb` stays cheap
    if name == "db":
        try:
            from .lmfdb_database import db
        except ImportError:
            print('Missing dependency; try running "sage -pip install -e ." in the LMFDB home folder.')
            raise
        globals()["db"] = db
        return db
    raise AttributeError("module 'lmfdb' has no attribute %r" % (name,))


def __dir__():
    return sorted(set(globals()) | {"db"})
