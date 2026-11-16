# Zenodo backup + LMFDB versioning: operations

Status: code merged but **not yet activated** — nothing talks to Zenodo until
the local config sets `enabled = true` *and* callers pass `live=True`, and the
version footer keeps showing the legacy string until `zenodo_setup()` is run.

## One-time setup (proddb)

1. Finalize [tables.yaml](tables.yaml): resolve every `review` entry to
   `yes`/`no` and assign `owner`s (Zenodo accounts) to the largest tables.
2. Create `~/.lmfdb_zenodo.ini` (mode 0600) on proddb; see the docstring in
   [config.py](config.py).  Start with `sandbox = true`.
3. In sage on proddb: `db.zenodo_setup()` — creates `version_history` (public
   schema; grants SELECT to the web role) and `userdb.zenodo_backups`, and
   records the initial major version from [lmfdb/version.py](../version.py).
   Run the same on grace (for beta's version page) with `ensure_tables`.
4. Weekly audit cron entry on proddb:

       0 3 * * 0     sage -python -c "from lmfdb import db; db.zenodo_audit()"

5. Code versions: the GitHub Action
   [code-version.yml](../../.github/workflows/code-version.yml) records each
   push to `web`.  Give it a role that can only add version rows, on proddb
   (and on grace, for beta):

       CREATE ROLE lmfdb_version LOGIN PASSWORD '...';
       GRANT SELECT, INSERT ON version_history TO lmfdb_version;
       GRANT USAGE ON SEQUENCE version_history_id_seq TO lmfdb_version;

   (plus a `pg_hba.conf` line if logins are restricted by role).  Do not
   reuse the `lmfdb` role behind `LMFDB_CI_ACCESS`: the web servers use it,
   and the test workflow hands it to every branch.  On GitHub, create an
   environment `lmfdb-version` whose deployment branches are limited to
   `web`, holding the secrets `LMFDB_VERSION_DSN` (e.g.
   `host=proddb.lmfdb.xyz dbname=lmfdb user=lmfdb_version password=...`) and
   optionally `LMFDB_VERSION_GRACE_DSN`.  If a run fails, rerun it from the
   Actions tab, or run `python3 -m lmfdb.zenodo.watcher` on proddb, which
   records the current head of `web`.
6. Zenodo side: make sure the `lmfdb` community exists and each owner's token
   (scopes `deposit:write` + `deposit:actions`) is in the config.

## Sandbox rehearsal, then backfill

1. With `sandbox = true`, run a full cycle on a couple of small tables:
   `db.zenodo_backfill(tables=[...], dry_run=False, live=True)`, then push one
   of them again to exercise the new-version path, then check the records on
   sandbox.zenodo.org.
2. Flip `sandbox = false`, then `db.zenodo_backfill(dry_run=True)` to see the
   batch plan, and run it for real off-peak (resumable; re-run after any
   interruption).  This creates data version `{MAJOR}.1` at the end.

## Per-push workflow (replaces the manual 2-step process)

Requests to move data to production use the "Move data to production" issue
form (`.github/ISSUE_TEMPLATE/data-to-prod.yml`), which asks for a
description of the change and whether it is a major or minor version update.
Copy both into the call:

    db.update_prod(["mf_newforms", "mf_hecke_traces"],
                   description="Added newforms of weight 1 and level up to 4000.",
                   bump="minor")

Either argument may be a dict by table name when tables differ.  This runs
`copy_to_from_remote` (devmirror → staging folder) + `reload_all` +
`zenodo_backup` (which skips unchanged tables, gives each changed table a new
record version with the description as its notes, refreshes the knowls
record, publishes the registry record, and increments the data version).
Until uploads are approved, the backup step defaults to a dry run: pass
`dry_run_backup=False, live=True` once they are.  A live run checks that
every already-archived table has a description and bump *before* copying
anything.

If an upload needs more than 50 GB it pauses with status `awaiting_quota`:
the owner raises the quota via "Manage storage" on the draft, then re-run
`db.zenodo_backup(folder, dry_run=False, live=True)` to resume (the
description and bump given originally are reused).  Quota above 50 GB/record
comes from a 150 GB allowance per Zenodo account (records under 50 GB use
none of it), so the large tables need to be spread across owners in
tables.yaml.  Zenodo's docs don't say whether a raised quota carries over to a
record's next version: check this in the sandbox rehearsal.

`db.zenodo_status()` reports the volume uploaded in the last 365 days.
Zenodo support (April 2026) described ~2 TB in total as fair use, but not
~2 TB uploaded every year.

## Version numbers

LMFDB versions are `{major}.{data}-{code}` (e.g. `2.3-5`); see
[lmfdb/version.py](../version.py) and the /version page.  Major bumps: edit
`MAJOR` in a PR; the code-version Action records the bump when it reaches
the `web` branch.  Nobody's release workflow changes.

Each table's Zenodo record has its own version `{major}.{minor}`, starting at
`1.0` and bumped as requested in the data request.  The knowls record gets a
minor bump whenever the knowls changed; the registry record's versions are
the LMFDB data versions themselves (`2.3`, ...).

## Safety properties

- No network to Zenodo unless `live=True` **and** `enabled = true` in config.
- Change detection hashes the *uncompressed* dump files; unchanged tables are
  never re-published, and unchanged files within a changed record are left to
  Zenodo's file-level deduplication (new-version drafts inherit files).
- Every step is resumable via `userdb.zenodo_backups` (including crashed
  uploads and quota pauses); `db.zenodo_audit()` catches anything missed.
- Published records are permanent: the md5 gate prevents junk versions.
