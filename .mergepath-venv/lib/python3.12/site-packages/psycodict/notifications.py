# -*- coding: utf-8 -*-
"""
LISTEN/NOTIFY support for psycodict: schema-change notifications and a small
general-purpose publish/subscribe primitive built on PostgreSQL's asynchronous
notification mechanism (``LISTEN``/``NOTIFY``/``pg_notify``).

Design
------

**Emission is transactional.**  Notifications are sent with
``SELECT pg_notify(channel, payload)`` executed on the database's *main*
connection, through the same ``_execute`` path (and therefore the same
transaction and ``DelayCommit`` bookkeeping) as every other statement.  This is
deliberate: PostgreSQL delivers a notification only when the transaction that
sent it commits, and drops it if that transaction rolls back.  A schema change
and its notification are thus atomic -- a listener never hears about a
``create_table`` that was rolled back, and always hears about one that
committed.  ``PostgresDatabase.notify`` and the internal schema hooks both rely
on this; when they run inside a ``DelayCommit`` block the notification rides the
surrounding transaction, and when they run standalone ``_execute`` commits
immediately (delivering at once).

**Listening uses a dedicated connection.**  A listener must *not* reuse the main
connection: that connection is busy running the application's transactions and
buffered server-side cursors, and a connection sitting in a transaction does not
see notifications committed by others until it ends that transaction.
:class:`NotificationListener` therefore opens its *own* psycopg connection from
the same :class:`~psycodict.config.Configuration` options, in ``autocommit``
mode, and issues ``LISTEN`` on it.  It is pull-based (synchronous): call
:meth:`~NotificationListener.poll` to collect whatever has arrived within a
bounded window, or iterate :meth:`~NotificationListener.listen`.  There are no
background threads and no thread-delivered callbacks by design -- a caller (such
as the LMFDB website) can wrap the pull loop in whatever concurrency model it
prefers.

**The schema channel contract.**  psycodict's schema-changing operations
(:meth:`~psycodict.database.PostgresDatabase.create_table`, ``drop_table``,
``rename_table``, :meth:`~psycodict.table.PostgresTable.add_column`,
``drop_column`` and the reload swap ``reload_final_swap``) each emit on the
single channel named by :data:`SCHEMA_CHANNEL` (``"psycodict_schema"``).  The
payload is *just the affected table's name*, as a plain string -- nothing else.
Keeping the payload to a bare table name keeps the contract simple and easy to
consume; a richer (e.g. JSON) payload describing exactly what changed is a
possible future extension, and is intentionally not attempted here.  A rename
emits twice, once for the old name and once for the new one, so that a listener
can drop the stale metadata and pick up the new table.

Reconnection
------------

Reconnection is intentionally *not* handled automatically.  If the listening
connection drops, :meth:`~NotificationListener.poll` / ``listen`` raise; a
long-lived listener should catch the error and build a fresh listener (any
notifications sent while it was disconnected are, per PostgreSQL semantics,
lost -- ``LISTEN`` only receives notifications sent after it was issued).
Keeping v1 free of silent auto-reconnect magic makes that loss visible to the
caller rather than hiding it.

Forking
-------

A listener, like any libpq connection, must not be used across ``fork()``:
parent and child would share one socket, so each would receive an
unpredictable subset of the notification stream, and an explicit ``close()``
in either process sends a protocol Terminate message over the shared socket,
killing the other process's subscription as well.  Create each listener in
the process that will poll it -- under a pre-forking web server (e.g.
``gunicorn --preload``) that means each worker builds its own listener after
the fork, for example lazily on first use, with ``os.getpid()`` recorded at
creation time to detect an inherited one.  A process that does find itself
holding a listener from before a fork should simply abandon the object: drop
the reference *without* calling ``close``.  That is safe -- psycopg
deliberately skips the protocol shutdown when a connection object is
garbage-collected in a process other than the one that created it, precisely
to protect the parent's copy.

Hot standbys
------------

Notifications do not traverse replication.  ``NOTIFY`` is not WAL-logged, so
nothing is delivered on physical replicas (nor by logical replication, which
publishes only data changes); moreover a server in recovery refuses the
subscription itself -- ``LISTEN`` raises ``cannot execute LISTEN during
recovery`` (SQLSTATE ``25006``), so building a listener against a hot
standby fails outright.  Treat that error as permanent for the server rather
than retrying: a process whose queries go to a standby must fall back to
refreshing on a schedule or on error, or subscribe on the primary (bearing
in mind that a notification can then arrive before the corresponding change
has replayed on the standby).
"""
import re

import psycopg
from psycopg.sql import SQL, Identifier

# The single channel on which psycodict announces schema changes.  The payload
# is the affected table's name.  See the module docstring for the contract.
SCHEMA_CHANNEL = "psycodict_schema"

# A NOTIFY/LISTEN channel is an SQL identifier.  We restrict the channels that
# psycodict will send or listen on to plain unquoted-identifier spellings
# (a leading letter or underscore, then letters, digits or underscores) so that
# a channel name can never smuggle in quoting or other surprises, and so that
# the name a sender uses always matches the name a listener uses.
_CHANNEL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def validate_channel_name(channel):
    """
    Check that ``channel`` is a plain identifier and return it, else raise.

    INPUT:

    - ``channel`` -- the candidate channel name

    OUTPUT: ``channel`` unchanged, if it is a non-empty string of letters,
    digits and underscores that does not start with a digit.
    """
    if not isinstance(channel, str) or not _CHANNEL_RE.match(channel):
        raise ValueError(
            "invalid notification channel %r: a channel must be a plain "
            "identifier (letters, digits and underscores, not starting with a "
            "digit)" % (channel,)
        )
    return channel


class NotificationListener:
    """
    A pull-based subscriber to one or more PostgreSQL notification channels.

    The listener owns a dedicated ``autocommit`` connection (separate from the
    database's main connection) built from the same configuration options, and
    issues ``LISTEN`` on each requested channel.  Retrieve notifications with
    :meth:`poll` (bounded, returns a list) or by iterating :meth:`listen`.

    It is a context manager; leaving the ``with`` block closes the connection::

        with db.listener() as listener:
            for channel, payload in listener.listen(timeout=60):
                ...

    A listener is bound to the process that created it and cannot subscribe
    on a server in recovery; see *Forking* and *Hot standbys* in the module
    docstring before using one in a forking application or against a replica.

    INPUT:

    - ``config`` -- a :class:`~psycodict.config.Configuration`; the
      ``postgresql`` options are used to open the dedicated connection
    - ``channels`` -- a channel name, or an iterable of them (default:
      ``("psycodict_schema",)``); each is validated and subscribed with
      ``LISTEN``
    - ``**connect_kwargs`` -- extra keyword arguments passed on to
      ``psycopg.connect`` (e.g. keepalive settings), overriding the
      configuration where they overlap
    """

    def __init__(self, config, channels=(SCHEMA_CHANNEL,), **connect_kwargs):
        if isinstance(channels, str):
            channels = (channels,)
        self.channels = tuple(validate_channel_name(c) for c in channels)
        if not self.channels:
            raise ValueError("a NotificationListener needs at least one channel")

        # Mirror PostgresDatabase._new_connection: start from the configured
        # postgresql options, let explicit keyword arguments override them.
        options = dict(config.options["postgresql"])
        options.update(connect_kwargs)
        # autocommit is essential: a connection sitting in an open transaction
        # does not receive notifications committed by other sessions.
        self._conn = psycopg.connect(**options, autocommit=True)
        try:
            for channel in self.channels:
                # The channel has been validated as a plain identifier;
                # Identifier still quotes it, so LISTEN is injection-safe.
                self._conn.execute(SQL("LISTEN {0}").format(Identifier(channel)))
        except Exception:
            self._conn.close()
            self._conn = None
            raise

    def _require_open(self):
        if self._conn is None or self._conn.closed:
            raise RuntimeError(
                "this NotificationListener's connection is closed; create a "
                "new listener (auto-reconnect is intentionally not provided)"
            )
        return self._conn

    def poll(self, timeout=0.0):
        """
        Return the notifications available within ``timeout`` seconds.

        Waits up to ``timeout`` seconds for the *first* notification, then
        returns it together with any others already buffered, without blocking
        further.  With ``timeout <= 0`` (the default) it does not wait at all,
        returning only what is already buffered.  A timed-out poll that saw
        nothing returns an empty list.

        OUTPUT: a list of ``(channel, payload)`` pairs, in arrival order.
        """
        conn = self._require_open()
        # Drain what is already buffered without blocking.
        result = [(n.channel, n.payload) for n in conn.notifies(timeout=0)]
        if not result and timeout and timeout > 0:
            # Nothing buffered yet: block up to `timeout` for the first one
            # (stop_after=1 returns as soon as it arrives rather than always
            # waiting the whole window), then drain any that came with it.
            result = [
                (n.channel, n.payload)
                for n in conn.notifies(timeout=timeout, stop_after=1)
            ]
            if result:
                result += [(n.channel, n.payload) for n in conn.notifies(timeout=0)]
        return result

    def listen(self, timeout=None):
        """
        Yield ``(channel, payload)`` pairs as notifications arrive.

        With ``timeout=None`` (the default) this blocks indefinitely, yielding
        each notification as it is received (until the connection is closed).
        With a numeric ``timeout`` the iterator stops after that many seconds,
        whether or not anything arrived.

        This is a thin wrapper over psycopg's own notification generator; break
        out of the loop (or close the listener) to stop early.
        """
        conn = self._require_open()
        for n in conn.notifies(timeout=timeout):
            yield (n.channel, n.payload)

    def close(self):
        """
        Close the dedicated connection.  Idempotent.
        """
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
