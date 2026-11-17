"""
Orchestration of the Zenodo backup pipeline.

The normal flow, run on proddb right after ``db.reload_all`` (see
``LMFDBDatabase.update_prod``):

    backup_folder(db, "/scratch/zenodo/2026-07-18")

which, for every eligible table whose dump files appear in the folder:

1. hashes the uncompressed dump files and skips the table if they match the
   last published version (no junk versions -- published versions are
   permanent);
2. packages the files (compression, splitting, README, sample, manifest);
3. creates a Zenodo deposition (or a new version of the table's record),
   uploads the files, publishes, and verifies checksums;
4. then refreshes the knowl-database record, increments the LMFDB data
   version, publishes the version-registry record, and records everything in
   ``version_history``.

Everything is written to be resumable: state lives in
``userdb.zenodo_backups`` and re-running ``backup_folder`` picks up
unfinished work (including drafts stuck waiting for a quota increase).

SAFETY: by default (``dry_run=True``, and ``live=False`` in the client) no
network traffic to Zenodo happens at all; a dry run reports what would be
uploaded.
"""

import os
from pathlib import Path

from . import metadata, packaging, state
from .client import (ZenodoClient, ZenodoError, NotFound, QuotaExceeded,
                     DEFAULT_QUOTA)
from .config import ZenodoConfig
from .versioning import BUMPS, format_version, next_record_version

KNOWLS_NAME = "lmfdb_knowls"
REGISTRY_NAME = "lmfdb_version_registry"
SPECIAL_RECORDS = [KNOWLS_NAME, REGISTRY_NAME]


######################################################################
# Table classification (tables.yaml)                                 #
######################################################################

BACKUP_VALUES = ("yes", "no", "hold", "review")

# archived before the rest of the backfill, for stage 2 of IGP24
BACKFILL_FIRST = ("gps_transitive", "lf_fields", "nf_fields", "nf_fields_extra")


def load_tables_yaml(path=None):
    """
    The archive/skip classification, as ``{tablename: {"backup":
    "yes"|"no"|"hold"|"review", "owner": ..., "note": ...}}``.
    """
    import yaml
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "tables.yaml")
    with open(path) as F:
        data = yaml.safe_load(F)
    spec = {}
    for name, entry in data["tables"].items():
        entry = dict(entry or {})
        backup = entry.get("backup")
        if backup is True:
            backup = "yes"
        elif backup is False:
            backup = "no"
        if backup not in BACKUP_VALUES:
            raise ValueError("bad backup value %r for %s" % (backup, name))
        entry["backup"] = backup
        spec[name] = entry
    return spec


def classify(names, spec):
    """
    Split table names by their ``backup`` value in tables.yaml, as a dict
    with keys ``yes``, ``no``, ``hold``, ``review`` and ``unlisted``.
    """
    split = {key: [] for key in BACKUP_VALUES + ("unlisted",)}
    for name in names:
        split[spec[name]["backup"] if name in spec else "unlisted"].append(name)
    return split


def _owner_for(name, spec, cfg, prev):
    """Sticky record ownership: previous attempt > tables.yaml > config."""
    if prev and prev.get("owner"):
        return prev["owner"]
    if name in spec and spec[name].get("owner"):
        return spec[name]["owner"]
    return cfg.default_owner


def _state_db(db, cfg):
    """
    The database object to keep archive state in: ``db`` itself, or for a
    sandbox configuration a ``state.Sandbox`` around it, whose state tables
    are created (with an initial version) on first use.
    """
    if not cfg.sandbox or isinstance(db, state.Sandbox):
        return db
    sdb = state.Sandbox(db)
    state.ensure_tables(sdb, grant_select_to=())
    if state.latest_versions(sdb) is None:
        state.insert_major(sdb, _current_major(), comment="sandbox rehearsal")
    return sdb


def _staging(cfg, staging_dir=None):
    """The staging directory, kept apart for sandbox rehearsals."""
    root = Path(staging_dir or cfg.staging_dir)
    return root / "sandbox" if cfg.sandbox else root


def _unfinished_tables(db):
    """Tables (not the knowls/registry records) with an upload in progress."""
    return sorted({r["tablename"] for r in state.unfinished(db)
                   if r["tablename"] not in SPECIAL_RECORDS})


######################################################################
# Uploading one packaged record                                      #
######################################################################

def _record_files(outdir, manifest):
    """{filename: (path, md5)} of everything to upload for a packaged record."""
    files = {}
    for path in packaging.upload_list(outdir):
        files[path.name] = (path, None)
    for art in manifest["artifacts"]:
        if "parts" in art:
            for part in art["parts"]:
                files[part["name"]] = (Path(outdir) / part["name"], part["md5"])
        else:
            files[art["name"]] = (Path(outdir) / art["name"], art["md5"])
    return {name: (path, md5) for name, (path, md5) in files.items()
            if path.exists()}


def _client(cfg, owner, live):
    return ZenodoClient(cfg.token_for(owner), sandbox=cfg.sandbox, live=live)


def _upload_record(db, client, cfg, attempt, name, outdir, manifest, deposit_md):
    """
    Drive one record from packaged files to published+verified, resuming a
    stored draft if present (``_reconcile`` must have run first).  Returns the
    updated attempt row dict on success, or None if paused awaiting a quota
    increase.
    """
    aid = attempt["id"]
    files = _record_files(outdir, manifest)
    total = sum(p.stat().st_size for p, _ in files.values())
    state.update_attempt(db, aid, total_size=total, status="uploading")

    if attempt.get("draft_id"):
        dep = client.get_deposition(attempt["draft_id"])
        if dep.get("submitted"):
            raise ZenodoError("draft %s of %s is already published; re-run to "
                              "record it" % (dep["id"], name))
    elif attempt.get("recid") or state.latest_published(db, name):
        prev = attempt.get("recid") or state.latest_published(db, name)["recid"]
        dep = client.new_version(prev)
    else:
        dep = client.create_deposition()
    dep_id = dep["id"]
    state.update_attempt(db, aid, draft_id=str(dep_id))
    client.update_metadata(dep_id, deposit_md)

    if total > DEFAULT_QUOTA:
        print("NOTE: %s needs %.1f GB > 50 GB; the owner (%s) may need to "
              "raise the quota via 'Manage storage' on the draft."
              % (name, total / 1e9, attempt["owner"]))

    # Upload anything not already present with the right checksum (files
    # inherited from the previous version or uploaded before a pause are
    # skipped, preserving Zenodo's file-level deduplication).
    existing = {f["filename"]: f.get("checksum", "")
                for f in client.list_files(dep_id)}
    bucket = dep["links"]["bucket"]
    # Remove stale files (e.g. renamed parts, files gone from this version)
    for f in client.list_files(dep_id):
        if f["filename"] not in files:
            client.delete_file(f["links"]["self"])
    before = attempt.get("uploaded_files") or {}
    uploaded = {}
    try:
        for fname, (path, md5) in sorted(files.items()):
            md5 = md5 or packaging.hash_file(path, count_lines=False)[1]
            if existing.get(fname, "").endswith(md5):
                # sent by this attempt before a pause, or inherited
                sent = before.get(fname, {})
                uploaded[fname] = (sent if sent.get("md5") == md5 else
                                   {"size": path.stat().st_size, "md5": md5,
                                    "reused": True})
                continue
            client.upload_file(bucket, path, name=fname)
            uploaded[fname] = {"size": path.stat().st_size, "md5": md5}
    except QuotaExceeded as err:
        state.update_attempt(db, aid, status="awaiting_quota",
                             uploaded_files=uploaded, error=str(err))
        print("PAUSED %s awaiting quota increase (%s); re-run to resume "
              "after raising it in the Zenodo UI." % (name, err))
        return None

    # saved first, so that a publication whose response is lost can still
    # be verified (see _reconcile)
    state.update_attempt(db, aid, uploaded_files=uploaded)
    published = client.publish(dep_id)
    return _record_publication(db, client, aid, name, published, uploaded)


def _record_publication(db, client, aid, name, published, uploaded):
    """Store a published deposition in the attempt and verify its files."""
    state.update_attempt(
        db, aid,
        status="published",
        recid=str(published["id"]),
        doi=published.get("doi"),
        concept_recid=str(published.get("conceptrecid", "")) or None,
        concept_doi=published.get("conceptdoi"),
        uploaded_files=uploaded,
        draft_id=None,
        finished=state.utcnow(),
        error=None,
    )
    return _verify(db, client, aid, name, published["id"], uploaded)


def _verify(db, client, aid, name, recid, uploaded):
    """
    Compare a published record with the files the attempt uploaded (each
    checked against the local package as it went up), marking the attempt
    verified if they agree.  Returns the attempt row.
    """
    if uploaded:
        problems = client.verify_record(
            recid, {f: info["md5"] for f, info in uploaded.items()})
    else:
        problems = ["no record of the uploaded files"]
    if problems:
        state.update_attempt(db, aid, error="; ".join(problems))
        print("VERIFICATION PROBLEMS for %s: %s" % (name, problems))
    else:
        state.update_attempt(db, aid, status="verified", error=None)
    return state.get_attempt(db, aid)


def _reconcile(db, cfg, live, names):
    """
    Bring the attempts for the records ``names`` up to date with Zenodo before
    anything new is planned or uploaded:

    - an unfinished attempt whose draft has been published (by a run whose
      response was lost) is recorded as published, with that attempt's own
      source hashes, so that newer content becomes a new version;
    - an unfinished attempt whose draft no longer exists forgets it;
    - the latest publication of each record is verified again if it is not
      yet verified.
    """
    names = set(names)
    for row in state.unfinished(db):
        name = row["tablename"]
        if name not in names or not row["draft_id"]:
            continue
        client = _client(cfg, row["owner"], live)
        try:
            dep = client.get_deposition(row["draft_id"])
        except NotFound:
            state.update_attempt(db, row["id"], draft_id=None,
                                 error="draft %s no longer exists on Zenodo"
                                 % row["draft_id"])
            continue
        if dep.get("submitted"):
            print("%s: draft %s was published by an earlier run; recording it"
                  % (name, dep["id"]))
            _record_publication(db, client, row["id"], name, dep,
                                row["uploaded_files"])
    for name in sorted(names):
        row = state.latest_published(db, name)
        if row is not None and row["status"] == "published":
            _verify(db, _client(cfg, row["owner"], live), row["id"], name,
                    row["recid"], row["uploaded_files"])


def _remove_package(staging, name):
    """Delete a record's package from the staging area, if present."""
    import shutil
    if (Path(staging) / name).exists():
        shutil.rmtree(Path(staging) / name)


def _sweep_packages(db, staging):
    """
    Delete packages left in the staging area (e.g. by a crash) for records
    whose latest attempt is verified; packages of paused or unresolved
    attempts are kept.
    """
    if not Path(staging).exists():
        return
    for folder in Path(staging).iterdir():
        row = state.latest_attempt(db, folder.name)
        if row is not None and row["status"] == "verified":
            _remove_package(staging, folder.name)


######################################################################
# The main entry point                                               #
######################################################################

FIRST_VERSION_NOTES = "First version archived on Zenodo."


def _for_table(value, name):
    """``value`` itself, or ``value[name]`` when it is a dict keyed by table."""
    if isinstance(value, dict):
        return value.get(name)
    return value


def _change_info(db, name, prev, description, bump, md5s=None):
    """
    The record version, bump and notes for uploading a new version of
    ``name`` (whose latest published attempt is ``prev``), as a dict with keys
    ``version``, ``bump``, ``notes`` and ``missing`` (the arguments that still
    need to be supplied).

    When ``md5s`` matches an interrupted attempt, that attempt's bump and
    notes fill in for missing arguments, so resuming needs neither.
    """
    notes, how = _for_table(description, name), _for_table(bump, name)
    if how is not None and how not in BUMPS:
        raise ValueError("bump for %s must be one of %s, not %r"
                         % (name, ", ".join(BUMPS), how))
    if md5s is not None:
        last = state.latest_attempt(db, name)
        if (last and last["status"] in state.UNFINISHED
                and last["source_md5s"] == md5s):
            notes = notes or last["notes"]
            how = how or last["bump"]
    if prev is None:
        return {"version": next_record_version(None, None), "bump": None,
                "notes": notes or FIRST_VERSION_NOTES, "missing": []}
    missing = [arg for arg, val in [("bump", how), ("description", notes)]
               if not val]
    return {"version": None if how is None
            else next_record_version(prev["version"], how),
            "bump": how, "notes": notes, "missing": missing}


def require_change_info(db, tables, description, bump, config=None):
    """
    Raise ValueError unless every eligible table among ``tables`` that
    already has a published record is given both a ``bump`` and a
    ``description``.  Used to fail fast before pushing tables to production.
    """
    db = _state_db(db, config or ZenodoConfig())
    include = classify(tables, load_tables_yaml())["yes"]
    missing = {}
    for name in include:
        info = _change_info(db, name, state.latest_published(db, name),
                            description, bump)
        if info["missing"]:
            missing[name] = info["missing"]
    if missing:
        raise ValueError(_missing_message(missing))


def _missing_message(missing):
    return ("For tables that already have a Zenodo record, give a "
            "description of the change and whether it is a major or minor "
            "version update (description=..., bump='minor'|'major'; either "
            "may be a dict by table name).  Missing: %s"
            % "; ".join("%s (%s)" % (name, ", ".join(args))
                        for name, args in sorted(missing.items())))


def backup_folder(db, data_folder, tables=None, dry_run=True, live=False,
                  config=None, editor=None, comment=None, staging_dir=None,
                  finalize_version=True, force=False, description=None,
                  bump=None, source_time=None):
    """
    Archive the tables whose dump files are in ``data_folder`` (the folder
    just passed to ``reload_all``) on Zenodo.

    INPUT:

    - ``tables`` -- restrict to these tables (default: everything found)
    - ``description`` -- what changed, as supplied by the contributor of the
      data; shown on each new Zenodo version.  A string applying to every
      table, or a dict by table name.  Required for tables that already have
      a published record.
    - ``bump`` -- ``"major"`` or ``"minor"`` (or a dict by table name): how
      the record version of each changed table is incremented.  Required
      like ``description``; first versions are always ``1.0``.
    - ``dry_run`` -- report what would happen without packaging or uploading
      (or contacting Zenodo: the live run first checks unfinished drafts,
      which can change the plan if a publication's response was lost)
    - ``live`` -- must be True (in addition to ``dry_run=False`` and
      ``enabled = true`` in the local config) for any network traffic
    - ``editor``, ``comment`` -- recorded in the version history (``comment``
      defaults to ``description`` when that is a string)
    - ``finalize_version`` -- allocate the next data version, refresh the
      knowls and registry records and write ``version_history``, once no
      table upload is unfinished (set to False by ``backfill``, which
      finalizes once at the end)
    - ``force`` -- upload even if the table matches its last published version
    - ``source_time`` -- when the dumps matched production (naive UTC), for
      ``audit``: ``update_prod`` passes the end of its reload; by default the
      time the dump files were written

    When resuming an interrupted upload of the same content, ``description``
    and ``bump`` default to those given originally.

    Returns a report dict.
    """
    cfg = config or ZenodoConfig()
    db = _state_db(db, cfg)
    spec = load_tables_yaml()
    editor = editor or cfg.editor
    if comment is None and isinstance(description, str):
        comment = description

    found = packaging.discover_tables(data_folder)
    if tables is not None:
        missing = set(tables) - set(found)
        if missing:
            raise ValueError("no dump files for %s in %s"
                             % (", ".join(sorted(missing)), data_folder))
        found = [t for t in found if t in tables]
    split = classify(found, spec)
    include = split["yes"]
    staging = _staging(cfg, staging_dir) / "records"
    if not dry_run:
        _require_enabled(cfg)
        _reconcile(db, cfg, live, include)
        _sweep_packages(db, staging)

    pending_version = format_version(*state.next_data_version(db))

    plan = {
        "version": pending_version,
        "upload": [],
        "skip_unchanged": [],
        "excluded": split["no"],
        "held": split["hold"],
        "review": split["review"],
        "unlisted": split["unlisted"],
        "published": {},
        "paused": [],
    }
    for name in include:
        md5s = packaging.source_md5s(data_folder, name)
        prev = state.latest_published(db, name)
        if (not force and prev and prev["status"] == "verified"
                and prev["source_md5s"] == md5s):
            plan["skip_unchanged"].append(name)
            continue
        size = sum(p.stat().st_size
                   for p in packaging.table_files(data_folder, name))
        item = {
            "table": name,
            "first_version": prev is None,
            "previous_version": prev and prev["version"],
            "owner": _owner_for(name, spec, cfg, prev) or "UNASSIGNED",
            "uncompressed_bytes": size,
            "source_md5s": md5s,
            "source_time": source_time or packaging.files_time(data_folder, name),
        }
        item.update(_change_info(db, name, prev, description, bump, md5s))
        plan["upload"].append(item)

    _print_plan(plan, dry_run)
    if dry_run:
        return plan
    missing = {item["table"]: item["missing"] for item in plan["upload"]
               if item["missing"]}
    if missing:
        raise ValueError(_missing_message(missing))

    for item in plan["upload"]:
        name = item["table"]
        if item["owner"] == "UNASSIGNED":
            raise ValueError("no owner for %s: set it in tables.yaml or "
                             "default_owner in %s" % (name, cfg.path))
        version, notes = item["version"], item["notes"]
        attempt = _resume_or_start(db, name, item)
        state.update_attempt(db, attempt["id"], status="packaging")
        manifest = packaging.package_table(
            data_folder, name, staging,
            chunk_gb=cfg.chunk_gb, level=cfg.compression_level,
            lmfdb_version=pending_version, record_version=version,
            readme=metadata.table_readme(db, name, version,
                                         lmfdb_version=pending_version,
                                         notes=notes))
        nrows = manifest["source_files"][name + ".txt"]["rows"]
        deposit_md = metadata.deposit_metadata(
            metadata.table_title(name),
            metadata.table_description_html(db, name, version, nrows,
                                            lmfdb_version=pending_version,
                                            notes=notes),
            version,
            community=cfg.community,
            related_url="%s/api/%s" % (metadata.LMFDB_URL, name),
            notes=notes)
        row = _upload_record(db, _client(cfg, attempt["owner"], live), cfg,
                             attempt, name, staging / name, manifest,
                             deposit_md)
        if row is None:
            plan["paused"].append(name)
        else:
            plan["published"][name] = _tables_entry(row)
            if row["status"] == "verified":
                _remove_package(staging, name)

    if finalize_version:
        waiting = _unfinished_tables(db)
        if waiting:
            # The data version must map every pushed table to its new record,
            # so it waits until the paused uploads are resumed and published.
            plan["version"] = None
            print("Not creating a data version yet: uploads unfinished for %s."
                  "  Resolve them and re-run zenodo_backup on the same folder."
                  % ", ".join(waiting))
        else:
            plan["version"] = finalize(db, cfg=cfg, live=live, editor=editor,
                                       comment=comment)
    return plan


def _require_enabled(cfg):
    if not cfg.enabled:
        raise RuntimeError(
            "Uploads are disabled (%s).  Set enabled = true in the [zenodo] "
            "section once the managing editors approve." % cfg.path)


def _resume_or_start(db, name, item):
    """
    Reuse an unfinished attempt for the same content.  Otherwise start a new
    attempt, retiring any unfinished ones for the record (so that they cannot
    block finalization) and taking over the latest one's draft and owner:
    the upload then replaces that draft's files, leaving no orphaned draft.
    Only valid after ``_reconcile``, which records drafts that were in fact
    published under the attempt they belong to.
    """
    prev = state.latest_attempt(db, name)
    if (prev and prev["status"] in state.UNFINISHED
            and prev["source_md5s"] == item["source_md5s"]):
        state.update_attempt(db, prev["id"], version=item["version"],
                             bump=item["bump"], notes=item["notes"])
        return state.latest_attempt(db, name)
    stale = [r for r in state.unfinished(db) if r["tablename"] == name]
    drafts = [r for r in stale if r["draft_id"]]
    owner = drafts[-1]["owner"] if drafts else item["owner"]
    aid = state.start_attempt(db, name, owner, item["version"],
                              item["source_md5s"], bump=item["bump"],
                              notes=item["notes"],
                              source_time=item["source_time"])
    for r in stale:
        state.update_attempt(db, r["id"], status="superseded",
                             error="superseded by attempt %s" % aid)
    if drafts:
        state.update_attempt(db, aid, draft_id=drafts[-1]["draft_id"])
    return state.latest_attempt(db, name)


def _tables_entry(row):
    return {"version": row["version"], "recid": row["recid"],
            "doi": row["doi"], "concept_doi": row["concept_doi"],
            "notes": row.get("notes")}


def _current_major():
    from lmfdb.version import MAJOR
    return MAJOR


def _print_plan(plan, dry_run):
    print("LMFDB data version to be created: %s%s"
          % (plan["version"], "  (dry run)" if dry_run else ""))
    total = sum(i["uncompressed_bytes"] for i in plan["upload"])
    print("To upload: %d tables, %.1f GB uncompressed"
          % (len(plan["upload"]), total / 1e9))
    for item in plan["upload"]:
        if item["first_version"]:
            change = "new record, version %s" % item["version"]
        else:
            change = "%s -> %s (%s)" % (item["previous_version"],
                                        item["version"] or "?",
                                        item["bump"] or "bump missing")
        print("  %-35s %8.2f GB  owner=%s  %s"
              % (item["table"], item["uncompressed_bytes"] / 1e9,
                 item["owner"], change))
        if item["notes"]:
            print("  %-35s notes: %s" % ("", item["notes"]))
    missing = {item["table"]: item["missing"] for item in plan["upload"]
               if item["missing"]}
    if missing:
        print("MISSING: " + _missing_message(missing))
    for key, label in [("skip_unchanged", "unchanged since last archive"),
                       ("excluded", "excluded by tables.yaml"),
                       ("held", "ON HOLD in tables.yaml (skipped)"),
                       ("review", "PENDING REVIEW in tables.yaml (skipped)"),
                       ("unlisted", "NOT CLASSIFIED in tables.yaml (skipped)")]:
        if plan[key]:
            print("%s: %s" % (label, ", ".join(plan[key])))


######################################################################
# Version finalization (knowls + registry + version_history)         #
######################################################################

def finalize(db, cfg=None, live=False, editor=None, comment=None):
    """
    Complete a data push: refresh the knowl-database record, assign the next
    data version to all published attempts not yet in a recorded data
    version, publish the registry record, and write ``version_history``.
    Called automatically by
    ``backup_folder`` unless ``finalize_version=False``.  Raises if any table
    upload is unfinished or any record of the batch fails verification.
    Re-running after an interruption resumes the knowls and registry records
    where they stopped.
    """
    cfg = cfg or ZenodoConfig()
    _require_enabled(cfg)
    db = _state_db(db, cfg)
    editor = editor or cfg.editor
    waiting = _unfinished_tables(db)
    if waiting:
        raise RuntimeError("uploads unfinished for %s; a data version can only "
                           "be created once they are published"
                           % ", ".join(waiting))
    owner = cfg.default_owner
    if owner is None:
        raise ValueError("default_owner must be set in %s" % cfg.path)
    recorded = state.recorded_data_versions(db)
    pending = [name for name, row in state.all_latest_published(db).items()
               if name not in SPECIAL_RECORDS
               and row["lmfdb_version"] not in recorded]
    _reconcile(db, cfg, live, pending + SPECIAL_RECORDS)
    unverified = [name for name in pending
                  if state.latest_published(db, name)["status"] != "verified"]
    if unverified:
        raise RuntimeError(
            "not verified on Zenodo: %s (see the error column of "
            "userdb.zenodo_backups); once resolved, re-run, or upload a "
            "corrected version with force=True" % ", ".join(unverified))
    major, seq = state.next_data_version(db)
    version = format_version(major, seq)
    staging = _staging(cfg) / "records"

    # 1. Knowls record (refreshed on every data push, since knowls change
    # live); its record version gets a minor bump each time
    prev = state.latest_published(db, KNOWLS_NAME)
    kbump = None if prev is None else "minor"
    kversion = next_record_version(prev and prev["version"], kbump)
    manifest = packaging.package_knowls(
        state.unwrap(db), staging, chunk_gb=cfg.chunk_gb,
        level=cfg.compression_level,
        lmfdb_version=version, record_version=kversion,
        readme=metadata.knowls_readme(version))
    md5s = {f: info["md5"] for f, info in manifest["source_files"].items()}
    tables_dict = {}
    if prev and prev["status"] == "verified" and prev["source_md5s"] == md5s:
        tables_dict[KNOWLS_NAME] = _tables_entry(prev)
    else:
        knotes = "Knowls as of LMFDB data version %s." % version
        attempt = _resume_or_start(db, KNOWLS_NAME, {
            "owner": owner, "version": kversion, "bump": kbump,
            "notes": knotes, "source_md5s": md5s, "source_time": None})
        deposit_md = metadata.deposit_metadata(
            "LMFDB knowledge database (knowls)",
            metadata.knowls_description_html(version), kversion,
            community=cfg.community,
            related_url="%s/knowledge/" % metadata.LMFDB_URL, notes=knotes)
        row = _upload_record(db, _client(cfg, attempt["owner"], live), cfg,
                             attempt, KNOWLS_NAME, staging / KNOWLS_NAME,
                             manifest, deposit_md)
        _require_verified(row, KNOWLS_NAME)
        tables_dict[KNOWLS_NAME] = _tables_entry(row)
    _remove_package(staging, KNOWLS_NAME)

    # 2. Assign the data version to the published attempts not yet in one
    # (including any stamped by an interrupted finalize with a version that
    # was never recorded, e.g. before a major bump)
    batch = {}
    for name, row in state.all_latest_published(db).items():
        if name != REGISTRY_NAME and row["lmfdb_version"] not in recorded:
            if row["lmfdb_version"] != version:
                state.update_attempt(db, row["id"], lmfdb_version=version)
            batch[name] = _tables_entry(row)
    batch.update(tables_dict)

    # 3. Registry record: full table -> record/version mapping at this
    # version; its record versions are the LMFDB data versions themselves
    registry = build_registry(db, version)
    regdir = staging / REGISTRY_NAME
    regdir.mkdir(parents=True, exist_ok=True)
    regfile = regdir / "lmfdb_version_registry.json"
    import json
    with open(regfile, "w") as F:
        json.dump(registry, F, indent=2, default=str)
        F.write("\n")
    reg_md5s = {regfile.name: packaging.hash_file(regfile)[1]}
    prev = state.latest_published(db, REGISTRY_NAME)
    if prev and prev["status"] == "verified" and prev["source_md5s"] == reg_md5s:
        row = prev  # published by an interrupted finalize of this version
    else:
        reg_notes = "Registry for LMFDB data version %s." % version
        attempt = _resume_or_start(db, REGISTRY_NAME, {
            "owner": owner, "version": version, "bump": None,
            "notes": reg_notes, "source_md5s": reg_md5s, "source_time": None})
        state.update_attempt(db, attempt["id"], lmfdb_version=version)
        deposit_md = metadata.deposit_metadata(
            "LMFDB version registry", metadata.registry_description_html(),
            version, community=cfg.community,
            related_url="%s/version" % metadata.LMFDB_URL, notes=reg_notes)
        row = _upload_record(db, _client(cfg, attempt["owner"], live), cfg,
                             attempt, REGISTRY_NAME, regdir,
                             {"artifacts": [], "source_files": {}}, deposit_md)
        _require_verified(row, REGISTRY_NAME)
    batch[REGISTRY_NAME] = _tables_entry(row)
    _remove_package(staging, REGISTRY_NAME)

    # 4. Write the version history
    row = state.version_row(major, "data", seq, editor=editor, tables=batch,
                            comment=comment)
    state.insert_version_rows(db, [row])
    print("Created LMFDB data version %s (%d records)" % (version, len(batch)))
    return version


def _require_verified(row, name):
    if row is None:
        raise RuntimeError("%s upload paused awaiting quota; resolve and "
                           "re-run finalize" % name)
    if row["status"] != "verified":
        raise RuntimeError("%s record %s not verified: %s; resolve and re-run "
                           "finalize" % (name, row["recid"], row["error"]))


def build_registry(db, version):
    """
    The JSON content of the registry record for a given data version.  It is
    a function of the archive state alone (no timestamp of its own), so that
    an interrupted finalize can recognize a registry it already published.
    """
    published = state.all_latest_published(db)
    return {
        "lmfdb_version": version,
        "tables": {name: _tables_entry(row)
                   for name, row in published.items()
                   if name != REGISTRY_NAME},
        "history": [
            {k: row[k] for k in ("major", "kind", "seq", "time", "git_hash",
                                 "comment") if row.get(k) is not None}
            for row in state.history(db)
        ],
    }


######################################################################
# Backfill, audit, status                                            #
######################################################################

DUMP_COMPLETE = ".dump-complete"


def _dump_once(db, tablename, folder):
    """
    Dump ``tablename`` into ``folder`` unless a completed dump is already
    there; a folder without the completion marker (an interrupted dump) is
    discarded and dumped again.  Returns the time the dump started (naive
    UTC), which the marker records.
    """
    import shutil
    from datetime import datetime
    folder = Path(folder)
    marker = folder / DUMP_COMPLETE
    if marker.exists():
        return datetime.fromisoformat(marker.read_text().split()[1])
    if folder.exists():
        shutil.rmtree(folder)
    started = state.utcnow()
    db.copy_to([tablename], folder)
    marker.write_text("%s %s\n" % (tablename, started.isoformat()))
    return started


def backfill(db, tables=None, dry_run=True, live=False, config=None,
             editor=None, first=BACKFILL_FIRST):
    """
    Initial population of the archive: dump each eligible table *from the
    production database itself*, the tables ``first`` in that order and then
    the rest smallest first, upload it, and delete its dump; once every table
    is published, create a single data version covering them all.  Tables on
    hold in tables.yaml are skipped.

    Resumable: published tables are skipped, completed dumps are reused (an
    interrupted dump is redone), and a table paused for a quota increase
    keeps its dump so that re-running resumes its upload.  Peak disk use is
    one table's dump plus its compressed copy (plus the dumps and packages
    of paused or unverified tables).  Run off-peak; dumping reads from the
    live production database.
    """
    import shutil
    cfg = config or ZenodoConfig()
    sdb = _state_db(db, cfg)
    spec = load_tables_yaml()
    if tables is None:
        tables = [t for t in db.tablenames if t in spec
                  and spec[t]["backup"] == "yes"]
    split = classify(tables, spec)
    include = split["yes"]
    todo = [t for t in include if state.latest_published(sdb, t) is None]

    sizes = db.table_sizes()

    def est(t):
        s = sizes.get(t, {})
        return (s.get("table_bytes", 0) or 0) + (s.get("toast_bytes", 0) or 0) \
            + (s.get("extras_bytes", 0) or 0)

    first = list(first or ())
    todo.sort(key=lambda t: (first.index(t) if t in first else len(first),
                             est(t)))
    print("Backfill: %d tables, %.1f GB, in this order; %d already archived"
          % (len(todo), sum(est(t) for t in todo) / 1e9,
             len(include) - len(todo)))
    for t in todo:
        print("  %-35s %8.2f GB" % (t, est(t) / 1e9))
    if split["hold"]:
        print("On hold in tables.yaml (skipped): %s" % ", ".join(split["hold"]))
    if dry_run:
        return todo

    root = _staging(cfg) / "backfill"
    if root.exists():  # dumps of tables published since, e.g. before a crash
        for folder in root.iterdir():
            if folder.name not in todo:
                shutil.rmtree(folder)
    paused = []
    for t in todo:
        folder = root / t
        dumped = _dump_once(db, t, folder)
        plan = backup_folder(sdb, folder, tables=[t], dry_run=False, live=live,
                             config=cfg, editor=editor, finalize_version=False,
                             source_time=dumped)
        if t in plan["paused"]:
            paused.append(t)
        else:
            shutil.rmtree(folder)
    if paused:
        print("Not creating the data version yet: %s awaiting a quota "
              "increase.  Raise it on the draft and re-run the backfill."
              % ", ".join(paused))
        return None
    return finalize(sdb, cfg=cfg, live=live, editor=editor,
                    comment="initial backfill")


def audit(db, config=None):
    """
    Cross-check the archive against reality; returns (and prints) a report:

    - tables reloaded on production (per userdb.dbrecord) after their last
      archived version
    - eligible tables never archived
    - tables in db.tablenames missing from tables.yaml, on hold, or pending
      review
    - unfinished or failed upload attempts
    """
    from psycodict import SQL
    db = _state_db(db, config or ZenodoConfig())
    spec = load_tables_yaml()
    split = classify(db.tablenames, spec)
    include = split["yes"]
    published = state.all_latest_published(db)

    # compare against when the archived dump was taken, not when its upload
    # finished: a paused upload can publish a dump that production has since
    # replaced.  Every logged operation changes the dump (schema changes and
    # resorts included) except create_table_like, logged under its source.
    changed, never = [], []
    cur = db._execute(SQL(
        "SELECT tablename, MAX(time) FROM userdb.dbrecord "
        "WHERE operation <> 'create_table_like' GROUP BY tablename"))
    last_change = dict(cur)
    for name in include:
        row = published.get(name)
        if row is None:
            never.append(name)
        else:
            taken = row["source_time"] or row["finished"]
            if name in last_change and taken is not None \
                    and last_change[name] > taken:
                changed.append(name)

    report = {
        "changed_since_archive": changed,
        "never_archived": never,
        "unclassified": split["unlisted"],
        "on_hold": split["hold"],
        "pending_review": split["review"],
        "unfinished": state.unfinished(db),
        "failed": [r for r in
                   state._backup_rows(db, SQL(" WHERE status = 'failed'"), None)],
    }
    for key, val in report.items():
        if val:
            if key in ("unfinished", "failed"):
                print("%s: %s" % (key, ", ".join(
                    "%s(%s)" % (r["tablename"], r["status"]) for r in val)))
            else:
                print("%s: %s" % (key, ", ".join(val)))
    if not any(report.values()):
        print("Archive is up to date.")
    return report


def status(db, config=None):
    """Print a summary of the archive and version state."""
    db = _state_db(db, config or ZenodoConfig())
    if isinstance(db, state.Sandbox):
        print("(sandbox state)")
    cur = state.latest_versions(db)
    if cur is None:
        print("Versioning not yet activated (version_history empty).")
    else:
        print("Current version: %s"
              % format_version(cur["major"], cur["data_seq"], cur["code_seq"]))
    published = state.all_latest_published(db)
    print("%d records archived" % len(published))
    for row in state.unfinished(db):
        print("  in flight: %s (%s)" % (row["tablename"], row["status"]))
    # Zenodo support (April 2026) considers ~2 TB fair use, but not ~2 TB
    # uploaded every year
    from datetime import timedelta
    year = state.uploaded_bytes_since(db, state.utcnow() - timedelta(days=365))
    print("Uploaded to Zenodo in the last 365 days: %.1f GB" % (year / 1e9))
    return {"version": cur, "published": published, "uploaded_last_year": year}
