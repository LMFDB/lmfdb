"""
The LMFDB major version number.

The full LMFDB version has the form ``{major}.{data}-{code}`` (e.g. ``2.3-5``):

- ``major`` is bumped manually by the managing editors, by changing MAJOR below
  (a normal pull request; the code-version GitHub Action records the bump
  when it reaches the web branch).
- ``data`` is incremented whenever a batch of tables is pushed to production
  and archived on Zenodo.  It is stored in the ``version_history`` table, not here.
- ``code`` counts frontend releases (pushes to the web branch).  It is assigned
  by the GitHub Action ``.github/workflows/code-version.yml`` (running
  ``lmfdb.zenodo.watcher``) and stored in the ``version_history`` table.

The ``data`` and ``code`` components reset when MAJOR is bumped.  Each archived
table also carries its own Zenodo record version ``{major}.{minor}`` (e.g.
``1.4``), bumped as requested by whoever contributes the data change.

See https://www.lmfdb.org/version for the version history and for recovering
the per-table Zenodo versions and frontend git commit of any LMFDB version.
"""

MAJOR = 2

# Displayed until the versioning system is activated (i.e. as long as the
# version_history table is absent or empty on the database being served).
LEGACY_VERSION = "LMFDB Release 1.2.1"
