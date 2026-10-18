"""
The lazy ``lmfdb.db`` proxy.

This module must stay dependency-light: importing it (and hence ``import
lmfdb``) pulls in nothing beyond the standard library, creates no files and
opens no connections.  The heavy imports (psycodict and the PostgreSQL
driver) happen in :func:`_make_database`, the first time the database is
actually used.
"""

import threading


def _make_database(config=None, **kwargs):
    try:
        from .lmfdb_database import LMFDBDatabase
    except ModuleNotFoundError as e:
        # Replace the error only when the missing module is one of the
        # database dependencies; any other import failure is a real bug and
        # propagates untouched
        if (e.name or "").split(".")[0] in ("psycodict", "psycopg"):
            raise ModuleNotFoundError(
                "{} is required for database access; installing the lmfdb "
                'package (for example with "sage -pip install -e ." from '
                "the root of an LMFDB checkout) installs all dependencies"
                .format(e.name),
                name=e.name,
            ) from e
        raise
    return LMFDBDatabase(config=config, **kwargs)


class LazyDatabase:
    """
    A lazy stand-in for :class:`~lmfdb.lmfdb_database.LMFDBDatabase`.

    Creating this object is free: the database module is only imported, and
    the connection to postgres only established, the first time the object
    is actually used (an attribute is accessed, a table is looked up, etc.),
    or when :meth:`connect` is called explicitly.  Afterward it behaves
    exactly like the underlying :class:`LMFDBDatabase` by forwarding
    everything to it.

    Introspection is connection-free: ``repr``, ``bool``, ``dir`` and the
    :attr:`connected` property never trigger the import or the connection.
    """
    def __init__(self):
        object.__setattr__(self, "_lazy_instance", None)
        object.__setattr__(self, "_lazy_lock", threading.Lock())

    def connect(self, config=None, **kwargs):
        """
        Connect to the database, if not already connected, and return the
        underlying :class:`LMFDBDatabase`.

        INPUT:

        - ``config`` -- optional configuration, as for :class:`LMFDBDatabase`.
          It is an error to provide it if the connection has already been made.
        """
        instance = object.__getattribute__(self, "_lazy_instance")
        if instance is None:
            with object.__getattribute__(self, "_lazy_lock"):
                instance = object.__getattribute__(self, "_lazy_instance")
                if instance is None:
                    instance = _make_database(config=config, **kwargs)
                    object.__setattr__(self, "_lazy_instance", instance)
                    return instance
        if config is not None or kwargs:
            raise RuntimeError("The database connection has already been established; connection options have no effect")
        return instance

    @property
    def connected(self):
        """Whether the connection to postgres has been established."""
        return object.__getattribute__(self, "_lazy_instance") is not None

    def __getattr__(self, name):
        return getattr(self.connect(), name)

    def __setattr__(self, name, value):
        setattr(self.connect(), name, value)

    def __delattr__(self, name):
        delattr(self.connect(), name)

    def __getitem__(self, name):
        return self.connect()[name]

    def __dir__(self):
        # dir() must not trigger the connection; before it is made, only the
        # proxy's own attributes are listed
        names = set(object.__dir__(self))
        instance = object.__getattribute__(self, "_lazy_instance")
        if instance is not None:
            names.update(dir(instance))
        return sorted(names)

    def __bool__(self):
        # so that `assert db` and `if db:` do not force a connection
        return True

    def __repr__(self):
        instance = object.__getattribute__(self, "_lazy_instance")
        if instance is None:
            return "LMFDB database (not yet connected; will connect on first use)"
        return repr(instance)


db = LazyDatabase()
