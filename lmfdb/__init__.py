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
    # The db object is provided lazily (PEP 562), so that `import lmfdb`
    # stays cheap and never fails: connecting is deferred until first use
    if name == "db":
        try:
            from .lmfdb_database import db
        except ImportError as e:
            # Chain an AttributeError rather than letting the ImportError
            # propagate: introspection such as help(lmfdb) then keeps
            # working, while `from lmfdb import db` and `lmfdb.db` both
            # display this message together with the underlying error
            raise AttributeError(
                "lmfdb.db is unavailable because a dependency failed to "
                "import ({}); installing the package, for example with "
                '"sage -pip install -e ." from the root of an LMFDB '
                "checkout, installs all dependencies".format(e)
            ) from e
        globals()["db"] = db
        return db
    raise AttributeError("module 'lmfdb' has no attribute %r" % (name,))


def __dir__():
    return sorted(set(globals()) | {"db"})
