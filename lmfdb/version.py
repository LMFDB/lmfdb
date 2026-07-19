"""
The LMFDB major version number.

The full LMFDB version has the form ``{major}.{data}.{code}`` (e.g. ``2.3.ba``):

- ``major`` is bumped manually by the managing editors, by changing MAJOR below
  (a normal pull request; the deploy watcher detects the change when it reaches
  the web branch and records it in the version history).
- ``data`` is incremented whenever a batch of tables is pushed to production
  and archived on Zenodo.  It is stored in the ``version_history`` table, not here.
- ``code`` counts frontend releases (pushes to the web branch), encoded in the
  letter scheme of ``sage.databases.cremona`` (a=0, ..., z=25, ba=26).  It is
  assigned automatically by the deploy watcher (``lmfdb.zenodo.watcher``) and
  stored in the ``version_history`` table.

The ``data`` and ``code`` components reset when MAJOR is bumped.

See https://www.lmfdb.org/version for the version history and for recovering
the per-table Zenodo versions and frontend git commit of any LMFDB version.
"""

MAJOR = 2

# Displayed until the versioning system is activated (i.e. as long as the
# version_history table is absent or empty on the database being served).
LEGACY_VERSION = "LMFDB Release 1.2.1"
