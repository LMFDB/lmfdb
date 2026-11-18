# Zenodo backup + LMFDB versioning: operations

Status: code merged but **not yet activated** — nothing talks to Zenodo until
the local config sets `enabled = true` *and* callers pass `live=True`, and the
version footer keeps showing the legacy string until `zenodo_setup()` is run.

## One-time setup (proddb)

1. [tables.yaml](tables.yaml) is decided (2026-11-16).  Tables on `hold`
   wait for their issues to be fixed or for their owner's Zenodo token;
   change them to `yes` when ready, and the next backfill picks them up.
2. Create `~/.lmfdb_zenodo.ini` (mode 0600) on proddb; see the docstring in
   [config.py](config.py).  Start with `sandbox = true`.
3. In sage on proddb: `db.zenodo_setup()` — creates `version_history` (public
   schema; grants SELECT to the web role) and `userdb.zenodo_backups`, and
   records the initial major version from [lmfdb/version.py](../version.py).
   Beta has no version table (its footer says "LMFDB beta").
4. Weekly audit cron entry on proddb (`live=True` adds read-only lookups
   of every record in the community listing on Zenodo):

       0 3 * * 0     sage -python -c "from lmfdb import db; db.zenodo_audit(live=True)"

5. Code versions: the GitHub Action
   [code-version.yml](../../.github/workflows/code-version.yml) records each
   push to `web`.  Give it a role on proddb that can only add version rows:

       CREATE ROLE lmfdb_version LOGIN PASSWORD '...';
       GRANT SELECT, INSERT ON version_history TO lmfdb_version;
       GRANT USAGE ON SEQUENCE version_history_id_seq TO lmfdb_version;

   (plus a `pg_hba.conf` line if logins are restricted by role).  Do not
   reuse the `lmfdb` role behind `LMFDB_CI_ACCESS`: the web servers use it,
   and the test workflow hands it to every branch.  On GitHub, create an
   environment `lmfdb-version` whose deployment branches are limited to
   `web`, holding the secrets `LMFDB_VERSION_DSN` (e.g.
   `host=proddb.lmfdb.xyz dbname=lmfdb user=lmfdb_version password=...`).
   A run only records its commit while
   that commit is still the head of `web`, so a stale rerun cannot number
   an old commit after a newer deploy.  If the latest run failed, rerun it
   from the Actions tab, or run `python3 -m lmfdb.zenodo.watcher` on proddb,
   which records the current head of `web`.
6. Zenodo side: each owner's token (scopes `deposit:write` +
   `deposit:actions`) goes in the config under the key `tables.yaml` uses
   for them.  The `lmfdb` community exists, with review policy `closed`:
   each new record's inclusion then waits for a curator to accept it (new
   versions stay in the community).  To avoid accepting ~100 requests by
   hand during the backfill, make the owners curators and relax the review
   policy, or accept them in bulk afterwards.

## Sandbox rehearsal, then backfill

1. With `sandbox = true`, run a full cycle on a couple of small tables:
   `db.zenodo_backfill(tables=[...], dry_run=False, live=True)`, then push one
   of them again to exercise the new-version path, then check the records on
   sandbox.zenodo.org.  In sandbox mode all archive state lives in
   `userdb.zenodo_backups_sandbox` and `userdb.version_history_sandbox`
   (created on first use) and dumps and packages go to
   `{staging_dir}/sandbox`: the rehearsal leaves the production state, the
   public version history and the footer untouched.
2. Flip `sandbox = false`, then `db.zenodo_backfill(dry_run=True)` to see
   the plan, and run it for real off-peak.  Tables are dumped, uploaded and
   deleted one at a time: gps_transitive, lf_fields, nf_fields and
   nf_fields_extra first (for IGP24 stage 2; `BACKFILL_FIRST` in
   [backup.py](backup.py)), then smallest first, skipping tables on `hold`.
   Re-run after any interruption (completed dumps are reused, published
   tables skipped).  Once every
   table is published it creates data version `{MAJOR}.1`; while any upload
   is paused for quota, it does not.

## Per-push workflow (replaces the manual 2-step process)

Requests to move data to production use the "Move data to production" issue
form (`.github/ISSUE_TEMPLATE/data-to-prod.yml`), which asks for a
description of the change and whether it is a major or minor version update.
Push the request by its issue number:

    db.update_prod_from_issue(7123)

which reads the tables, description and bump from the issue (public GitHub
API, no token), prints them, and asks for confirmation before calling

    db.update_prod(["mf_newforms", "mf_hecke_traces"],
                   description="Added newforms of weight 1 and level up to 4000.",
                   bump="minor")

which can also be called directly.  Either argument may be a dict by table
name when tables differ.  This runs
`copy_to_from_remote` (devmirror → staging folder) + `reload_all` +
`zenodo_backup` (which skips unchanged tables, gives each changed table a new
record version with the description as its notes, refreshes the knowls
record, publishes the registry record, and increments the data version).
Until uploads are approved, the backup step defaults to a dry run: pass
`dry_run_backup=False, live=True` once they are.  A live run checks that
every already-archived table has a description and bump *before* copying
anything.

A record over 50 GB gets its draft's quota raised automatically (through
the API, with the owner's token) to its size rounded up to whole GB, never
below an earlier version's size, and only beyond what the pipeline set
before (so a larger quota set by hand stays).  If Zenodo refuses, typically because the
owner's allowance is used up, the upload pauses with status
`awaiting_quota` and the reason in its error: free some allowance or raise
the quota via "Manage storage" on the draft, then re-run
`db.zenodo_backup(folder, dry_run=False, live=True)` to resume (the
description and bump given originally are reused).  No data version is
created while any table upload is unfinished, so the push gets a single data
version, created by the run that completes it; keep the folder until then.  Quota above 50 GB/record
comes from a 150 GB allowance per Zenodo account (records under 50 GB use
none of it), so the large tables need to be spread across owners in
tables.yaml.  A raised quota belongs to the record as a whole: each new
version's draft inherits it, and it counts once against the allowance
(Zenodo's source, confirmed on the sandbox 2026-11-17).  The pipeline raises
it with `POST /api/records/<draft id>/quota-increase` and
`{"quota_size": "<total GB>"}`, which the owner's deposit token may call.
Separately, Zenodo's web proxy refuses any single upload above roughly
50 GB (between 51 and 55 GB on the sandbox), so keep `chunk_gb` well below
that.

`db.zenodo_status()` reports the volume uploaded in the last 365 days.
Zenodo support (April 2026) described ~2 TB in total as fair use, but not
~2 TB uploaded every year.

## Version numbers

LMFDB versions are `{major}.{data}-{code}` (e.g. `2.3-5`); see
[lmfdb/version.py](../version.py) and the /version page.  Major bumps: edit
`MAJOR` in a PR; the code-version Action records the bump when it reaches
the `web` branch.  Nobody's release workflow changes.  Data pushes take the
major from the version history, not from the editor's checkout, so a stale
session on proddb still numbers its push correctly.

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
  A live run first asks Zenodo about unfinished drafts, so a publication
  whose response was lost is credited to the dump it holds, and newer data
  becomes the next version.
- A data version is created only once every record in it is verified
  against the uploaded checksums.  Packages are deleted from the staging
  area once verified.
- Archive runs take a database lock, so overlapping pushes run one after
  the other.  A live `update_prod` holds it from the copy through the
  archive, so pushes are archived in the order they reached production; the
  backfill takes it one table at a time, so it does not hold pushes up.  Table and knowls records do not name a data version (it is
  assigned later); the registry record does, and is published only after
  its version is recorded.
- Published records are permanent: the md5 gate prevents junk versions.
- After each data version, its records are looked up in the community
  listing, which Zenodo builds from its search index.  That index can miss
  a record whose own metadata names the community (two records of the first
  backfill, 2026-11-18), so a record still missing after two minutes is
  re-published unchanged (same DOI, version and files), which has Zenodo
  index it again.  A record that is not in the community at all, e.g. one
  whose inclusion awaits a curator, is reported instead.
  `db.zenodo_audit(live=True)` reports records missing from the listing and
  `db.zenodo_reindex(live=True)` repairs them.
