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
4. Cron entries on proddb:

       */15 * * * *  python3 -m lmfdb.zenodo.watcher   # frontend releases
       0 3 * * 0     sage -python -c "from lmfdb import db; db.zenodo_audit()"

5. Zenodo side: make sure the `lmfdb` community exists and each owner's token
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

    db.update_prod(["mf_newforms", ...])

= `copy_to_from_remote` (devmirror → staging folder) + `reload_all` +
`zenodo_backup` (which skips unchanged tables, refreshes the knowls record,
publishes the registry record, and increments the data version).  Until
uploads are approved, the backup step defaults to a dry run: pass
`dry_run_backup=False, live=True` once they are.

If an upload needs more than 50 GB it pauses with status `awaiting_quota`:
the owner raises the quota via "Manage storage" on the draft (each account
has 150 GB to distribute above the free 50 GB/record), then re-run
`db.zenodo_backup(folder, dry_run=False, live=True)` to resume.

## Version numbers

`{major}.{data}.{code}` (e.g. `2.3.ba`) — see [lmfdb/version.py](../version.py)
and the /version page.  Major bumps: edit `MAJOR` in a PR; the watcher
detects it when it reaches the `web` branch.  Nobody's release workflow
changes: the watcher notices pushes to `web` via `git ls-remote`.

## Safety properties

- No network to Zenodo unless `live=True` **and** `enabled = true` in config.
- Change detection hashes the *uncompressed* dump files; unchanged tables are
  never re-published, and unchanged files within a changed record are left to
  Zenodo's file-level deduplication (new-version drafts inherit files).
- Every step is resumable via `userdb.zenodo_backups` (including crashed
  uploads and quota pauses); `db.zenodo_audit()` catches anything missed.
- Published records are permanent: the md5 gate prevents junk versions.
