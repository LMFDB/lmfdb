"""
Automatic backup of LMFDB tables to Zenodo, and the LMFDB version numbering
scheme built on top of it.

Overview
--------

Each search table gets its own Zenodo record (grouped under a concept DOI);
every time a table is pushed to production a new version of its record is
published (with a major or minor version bump and a description of the
change, as requested by the contributor of the data), containing exactly the
files that ``db.reload_all`` loaded (search/extras data, counts, stats,
indexes, constraints and meta files), each individually compressed,
together with a generated README, a plain-text sample for Zenodo's preview,
and a MANIFEST.json with checksums.  Two additional
records are maintained: one for the knowl database (updated on every data
push) and a small "version registry" record holding the full table -> version
mapping for every LMFDB version.

Submodules
----------

- ``versioning`` -- ``{major}.{data}-{code}`` LMFDB versions and
  ``{major}.{minor}`` record versions
- ``state`` -- the ``version_history`` and ``userdb.zenodo_backups`` tables
- ``packaging`` -- compression, splitting, manifests, samples
- ``metadata`` -- Zenodo deposit metadata, README/description generation
- ``client`` -- thin Zenodo REST client (safe by default: raises unless
  explicitly constructed with ``live=True``)
- ``backup`` -- orchestration (called from ``LMFDBDatabase`` methods)
- ``watcher`` -- deploy watcher assigning frontend code versions
- ``tables.yaml`` -- which tables are backed up, and by whom

Nothing here talks to Zenodo (or the network) unless explicitly asked to.
"""

from .versioning import format_version, parse_version

__all__ = ["format_version", "parse_version"]
