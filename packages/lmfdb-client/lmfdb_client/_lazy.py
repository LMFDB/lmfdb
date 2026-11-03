"""
The lazy database proxy behind ``lmfdb_client.db`` (and the LMFDB website's
``lmfdb.db``).

This module must stay dependency-light: importing it pulls in nothing beyond
the standard library, creates no files and opens no connections.  The heavy
imports (psycodict and the PostgreSQL driver) happen in the factory, the
first time the database is actually used.
"""

import threading

# The top-level modules that database access needs; a missing one is
# reported with installation instructions rather than a bare import error
_DATABASE_DEPENDENCIES = ("psycodict", "psycopg")


class LazyDatabase:
    """
    A lazy stand-in for a database object.

    Creating this object is free: the database is only created, and the
    connection to postgres only established, the first time the object is
    actually used (an attribute is accessed, a table is looked up, etc.), or
    when :meth:`connect` is called explicitly.  Afterward it behaves exactly
    like the underlying database by forwarding everything to it.

    Introspection is connection-free: ``repr``, ``bool``, ``dir`` and the
    :attr:`connected` property never trigger the import or the connection.

    INPUT:

    - ``factory`` -- a function taking ``config=None`` and keyword arguments
      and returning the database object; it is called at most once
    """
    def __init__(self, factory):
        object.__setattr__(self, "_lazy_factory", factory)
        object.__setattr__(self, "_lazy_instance", None)
        object.__setattr__(self, "_lazy_lock", threading.Lock())

    def connect(self, config=None, **kwargs):
        """
        Connect to the database, if not already connected, and return the
        underlying database object.

        INPUT:

        - ``config`` -- optional configuration, passed to the factory.  It is
          an error to provide it (or other keyword arguments) if the
          connection has already been made.
        """
        instance = object.__getattribute__(self, "_lazy_instance")
        if instance is None:
            with object.__getattribute__(self, "_lazy_lock"):
                instance = object.__getattribute__(self, "_lazy_instance")
                if instance is None:
                    factory = object.__getattribute__(self, "_lazy_factory")
                    try:
                        instance = factory(config=config, **kwargs)
                    except ModuleNotFoundError as e:
                        # Replace the error only when the missing module is
                        # one of the database dependencies; any other import
                        # failure is a real bug and propagates untouched
                        if (e.name or "").split(".")[0] in _DATABASE_DEPENDENCIES:
                            raise ModuleNotFoundError(
                                "{} is required for database access; it is installed by "
                                '"pip install lmfdb-client" (or, in an LMFDB checkout, by '
                                '"sage -pip install -r requirements.txt")'.format(e.name),
                                name=e.name,
                            ) from e
                        raise
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
