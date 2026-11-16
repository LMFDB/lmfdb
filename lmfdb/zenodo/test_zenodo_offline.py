"""
Offline tests for the Zenodo backup system: no database, no network, no sage
required (tests comparing against sage are skipped when it is absent).
"""

import gzip
import hashlib
import json
import os

import pytest

from lmfdb.zenodo.versioning import (
    format_version,
    next_record_version,
    parse_record_version,
    parse_version,
)
from lmfdb.zenodo import packaging
from lmfdb.zenodo.client import NotLive, ZenodoClient
from lmfdb.zenodo.config import ZenodoConfig
from lmfdb.zenodo import metadata


######################################################################
# versioning                                                         #
######################################################################

def test_format_parse_version():
    assert format_version(2, 3, 5) == "2.3-5"
    assert format_version(2, 0, 0) == "2.0-0"
    assert format_version(2, 3) == "2.3"
    assert parse_version("2.3-5") == (2, 3, 5)
    assert parse_version("2.0-0") == (2, 0, 0)
    assert parse_version("2.3") == (2, 3, None)
    assert parse_version(" 10.20-675 ") == (10, 20, 675)
    for bad in ["", "2", "2.3-", "2.3.ba", "1.2.1", "a.b-c", "2.-1-0",
                "2.3-a", "2.3-5-1"]:
        with pytest.raises(ValueError):
            parse_version(bad)
    with pytest.raises(ValueError):
        format_version(2, 3, -1)


def test_record_versions():
    assert next_record_version(None, None) == "1.0"
    assert next_record_version(None, "major") == "1.0"
    assert next_record_version("1.0", "minor") == "1.1"
    assert next_record_version("1.4", "major") == "2.0"
    assert next_record_version("9.9", "minor") == "9.10"
    assert parse_record_version("9.10") == (9, 10)
    with pytest.raises(ValueError):
        next_record_version("1.4", "patch")
    with pytest.raises(ValueError):
        next_record_version("1.4", None)
    for bad in ["1", "1.2.3", "2.3-5", "v1.0"]:
        with pytest.raises(ValueError):
            parse_record_version(bad)


######################################################################
# packaging                                                          #
######################################################################

SEP = "|"


def make_dump(folder, name="zzz_demo", nrows=20, extras=True):
    """A minimal but format-faithful psycodict dump folder."""
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / (name + ".txt"), "w") as F:
        F.write(SEP.join(["id", "label", "dim"]) + "\n")
        F.write(SEP.join(["bigint", "text", "integer"]) + "\n\n")
        for i in range(nrows):
            F.write(SEP.join([str(i), "lab.%s" % i, str(i * i)]) + "\n")
    if extras:
        with open(folder / (name + "_extras.txt"), "w") as F:
            F.write(SEP.join(["id", "bigdata"]) + "\n")
            F.write(SEP.join(["bigint", "jsonb"]) + "\n\n")
            for i in range(nrows):
                F.write(SEP.join([str(i), json.dumps(list(range(i)))]) + "\n")
    for end, rows in [("_counts.txt", 2), ("_stats.txt", 1),
                      ("_indexes.txt", 1), ("_constraints.txt", 0),
                      ("_meta.txt", 1)]:
        with open(folder / (name + end), "w") as F:
            for i in range(rows):
                F.write("row%s%sdata\n" % (i, SEP))
    return name


def test_discover_and_table_files(tmp_path):
    make_dump(tmp_path / "dump", "zzz_demo")
    make_dump(tmp_path / "dump", "zzz_other", extras=False)
    assert packaging.discover_tables(tmp_path / "dump") == ["zzz_demo",
                                                            "zzz_other"]
    files = packaging.table_files(tmp_path / "dump", "zzz_demo")
    assert [f.name for f in files] == [
        "zzz_demo.txt", "zzz_demo_extras.txt", "zzz_demo_counts.txt",
        "zzz_demo_stats.txt", "zzz_demo_indexes.txt",
        "zzz_demo_constraints.txt", "zzz_demo_meta.txt"]
    assert [f.name for f in packaging.table_files(tmp_path / "dump",
                                                  "zzz_other")] == [
        "zzz_other.txt", "zzz_other_counts.txt", "zzz_other_stats.txt",
        "zzz_other_indexes.txt", "zzz_other_constraints.txt",
        "zzz_other_meta.txt"]


def test_hash_file(tmp_path):
    p = tmp_path / "f.txt"
    data = b"hello\nworld\n"
    p.write_bytes(data)
    size, md5, sha256, nlines = packaging.hash_file(p)
    assert size == len(data)
    assert md5 == hashlib.md5(data).hexdigest()
    assert sha256 == hashlib.sha256(data).hexdigest()
    assert nlines == 2


def test_package_table(tmp_path):
    dump = tmp_path / "dump"
    name = make_dump(dump, nrows=50)
    staging = tmp_path / "staging"
    manifest = packaging.package_table(
        dump, name, staging, force_gzip=True, lmfdb_version="2.1",
        readme="# test readme\n", record_version="1.4")
    outdir = staging / name

    # sources: all seven files hashed, with correct row counts
    assert set(manifest["source_files"]) == {
        name + end for end in ["", "_extras", "_counts", "_stats", "_indexes",
                               "_constraints", "_meta"]
        for end in [end + ".txt"]}
    assert manifest["source_files"][name + ".txt"]["rows"] == 50
    assert manifest["source_files"][name + "_extras.txt"]["rows"] == 50
    assert manifest["source_files"][name + "_counts.txt"]["rows"] == 2
    assert manifest["source_files"][name + "_constraints.txt"]["rows"] == 0
    src = dump / (name + ".txt")
    assert (manifest["source_files"][name + ".txt"]["md5"]
            == hashlib.md5(src.read_bytes()).hexdigest())

    # artifacts decompress back to the sources
    for art in manifest["artifacts"]:
        blob = (outdir / art["name"]).read_bytes()
        assert len(blob) == art["size"]
        assert hashlib.md5(blob).hexdigest() == art["md5"]
        assert gzip.decompress(blob) == (dump / art["source"]).read_bytes()

    # sample: Markdown with 3 header lines + 10 rows of the search file, as
    # an indented code block; not a .txt file, which reload_all would load
    sample = (outdir / (name + "_sample.md")).read_text().splitlines()
    code = [line[4:] for line in sample if line.startswith("    ")]
    assert sample[0] == "# Sample of `%s`" % name
    assert code[0] == "id|label|dim" and code[3] == "0|lab.0|0"
    assert len(code) == 13
    assert not list(outdir.glob("*.txt"))

    # README and MANIFEST written; manifest on disk matches return value
    assert (outdir / "README.md").read_text() == "# test readme\n"
    ondisk = json.loads((outdir / "MANIFEST.json").read_text())
    assert ondisk == manifest
    assert manifest["lmfdb_version"] == "2.1"
    assert manifest["record_version"] == "1.4"

    # upload order: README, sample, MANIFEST, then artifacts
    names = [p.name for p in packaging.upload_list(outdir)]
    assert names[:3] == ["README.md", name + "_sample.md", "MANIFEST.json"]


def test_split_and_reassemble(tmp_path):
    dump = tmp_path / "dump"
    name = make_dump(dump, nrows=2000, extras=False)
    staging = tmp_path / "staging"
    # chunk of 5000 bytes forces the main artifact into several parts
    manifest = packaging.package_table(dump, name, staging, force_gzip=True,
                                       chunk_gb=5000 / 10**9)
    art = [a for a in manifest["artifacts"]
           if a["source"] == name + ".txt"][0]
    assert "parts" in art and len(art["parts"]) > 1
    assert art["reassemble"].startswith("cat ")
    outdir = staging / name
    assert not (outdir / art["name"]).exists()  # replaced by parts
    blob = b"".join((outdir / p["name"]).read_bytes() for p in art["parts"])
    assert len(blob) == art["size"]
    assert hashlib.md5(blob).hexdigest() == art["md5"]
    assert gzip.decompress(blob) == (dump / (name + ".txt")).read_bytes()
    for p in art["parts"]:
        assert p["size"] <= 5000
        assert (hashlib.md5((outdir / p["name"]).read_bytes()).hexdigest()
                == p["md5"])


@pytest.mark.skipif(not packaging.zstd_available(), reason="no zstd CLI")
def test_package_with_zstd(tmp_path):
    import subprocess
    dump = tmp_path / "dump"
    name = make_dump(dump, nrows=30, extras=False)
    manifest = packaging.package_table(dump, name, tmp_path / "staging")
    art = manifest["artifacts"][0]
    assert art["name"].endswith(".zst")
    out = subprocess.run(
        ["zstd", "-d", "-c", str(tmp_path / "staging" / name / art["name"])],
        capture_output=True, check=True)
    assert out.stdout == (dump / art["source"]).read_bytes()


def test_sample_truncation(tmp_path):
    dump = tmp_path / "dump"
    dump.mkdir()
    with open(dump / "zzz_big.txt", "w") as F:
        F.write("id|blob\nbigint|text\n\n")
        F.write("0|" + "x" * 10**6 + "\n")
    dst = dump / "sample.md"
    packaging.write_sample(dump / "zzz_big.txt", dst, max_bytes=1000)
    text = dst.read_text()
    assert len(text) < 2000
    assert "truncated for preview" in text


def test_source_md5s_change_detection(tmp_path):
    dump = tmp_path / "dump"
    name = make_dump(dump)
    before = packaging.source_md5s(dump, name)
    assert set(before) == {f.name for f in packaging.table_files(dump, name)}
    assert packaging.source_md5s(dump, name) == before
    with open(dump / (name + ".txt"), "a") as F:
        F.write("20|lab.20|400\n")
    after = packaging.source_md5s(dump, name)
    assert after != before
    assert after[name + "_extras.txt"] == before[name + "_extras.txt"]


######################################################################
# metadata                                                           #
######################################################################

def test_metadata_without_db():
    notes = "Added <weight 1> forms & fixed labels."
    desc = metadata.table_description_html(None, "zzz_demo", "1.4", nrows=17,
                                           lmfdb_version="2.3", notes=notes)
    assert "zzz_demo" in desc and "17" in desc
    assert "Version 1.4 of" in desc and "LMFDB data version 2.3" in desc
    assert "Added &lt;weight 1&gt; forms &amp; fixed labels." in desc
    readme = metadata.table_readme(None, "zzz_demo", "1.4",
                                   lmfdb_version="2.3", notes=notes)
    assert readme.startswith("# LMFDB table `zzz_demo`, version 1.4")
    assert "LMFDB data version 2.3" in readme
    assert "Changes in this version: " + notes in readme
    assert "reload_all" in readme
    md = metadata.deposit_metadata(
        metadata.table_title("zzz_demo"), desc, "1.4",
        related_url="https://www.lmfdb.org/api/zzz_demo",
        notes=notes)["metadata"]
    assert md["title"] == "LMFDB table zzz_demo"
    assert md["license"] == "cc-by-sa-4.0"
    assert md["creators"] == [{"name": "The LMFDB Collaboration"}]
    assert md["version"] == "1.4"
    assert md["notes"] == notes
    assert md["communities"] == [{"identifier": "lmfdb"}]
    assert md["upload_type"] == "dataset"
    assert md["related_identifiers"][0]["identifier"].endswith("zzz_demo")


######################################################################
# client safety                                                      #
######################################################################

def test_client_not_live():
    client = ZenodoClient("fake-token")
    assert not client.live
    with pytest.raises(NotLive):
        client.create_deposition()
    with pytest.raises(NotLive):
        client.get_record(12345)
    with pytest.raises(NotLive):
        client.upload_file("https://example.org/bucket", __file__)


######################################################################
# config                                                             #
######################################################################

def test_config_defaults_and_parsing(tmp_path):
    cfg = ZenodoConfig(path=str(tmp_path / "missing.ini"))
    assert not cfg.exists and not cfg.enabled and cfg.sandbox
    assert cfg.community == "lmfdb"
    path = tmp_path / "zenodo.ini"
    path.write_text("""
[zenodo]
enabled = true
sandbox = false
community = lmfdb
staging_dir = /scratch/z
chunk_gb = 10
editor = roed
default_owner = roed

[tokens]
roed = abc123
""")
    os.chmod(path, 0o600)
    cfg = ZenodoConfig(path=str(path))
    assert cfg.enabled and not cfg.sandbox
    assert cfg.chunk_gb == 10 and cfg.staging_dir == "/scratch/z"
    assert cfg.token_for("roed") == "abc123"
    with pytest.raises(ValueError):
        cfg.token_for("nobody")


######################################################################
# tables.yaml / eligibility (needs psycodict only for module import)  #
######################################################################

def test_tables_yaml():
    pytest.importorskip("psycodict")
    from lmfdb.zenodo.backup import load_tables_yaml, classify
    spec = load_tables_yaml()
    assert all(e["backup"] in ("yes", "no", "review") for e in spec.values())
    assert spec["nf_fields"]["backup"] == "yes"
    assert spec["gps_groups_test"]["backup"] == "no"
    include, excluded, review, unlisted = classify(
        ["nf_fields", "gps_groups_test", "totally_new_table"], spec)
    assert include == ["nf_fields"]
    assert excluded == ["gps_groups_test"]
    assert unlisted == ["totally_new_table"]


######################################################################
# record versions and change notes in the backup plan                #
######################################################################

def prod_config(tmp_path, enabled=False):
    """A configuration for the production archive (the default is sandbox)."""
    path = tmp_path / "zenodo.ini"
    path.write_text("[zenodo]\nenabled = %s\nsandbox = false\nstaging_dir = %s\n"
                    "default_owner = roed\n\n[tokens]\nroed = fake-token\n"
                    % ("true" if enabled else "false", tmp_path / "staging"))
    os.chmod(path, 0o600)
    return ZenodoConfig(path=str(path))


@pytest.fixture
def offline_backup(monkeypatch):
    """lmfdb.zenodo.backup with the database-backed state replaced by dicts."""
    pytest.importorskip("psycodict")
    from lmfdb.zenodo import backup, state
    published = {"zzz_demo": {"version": "1.4", "source_md5s": {},
                              "owner": "roed"}}
    attempts = {}
    monkeypatch.setattr(backup, "load_tables_yaml", lambda path=None: {
        "zzz_demo": {"backup": "yes"}, "zzz_other": {"backup": "yes"},
        "zzz_skip": {"backup": "no"}})
    monkeypatch.setattr(backup, "_current_major", lambda: 2)
    monkeypatch.setattr(state, "latest_published",
                        lambda db, name: published.get(name))
    monkeypatch.setattr(state, "latest_attempt",
                        lambda db, name, statuses=None: attempts.get(name))
    monkeypatch.setattr(state, "next_data_seq", lambda db, major: 3)
    return backup, published, attempts


def test_change_info(offline_backup, tmp_path):
    backup, published, attempts = offline_backup
    first = backup._change_info(None, "zzz_other", None, None, None)
    assert first == {"version": "1.0", "bump": None, "missing": [],
                     "notes": backup.FIRST_VERSION_NOTES}
    prev = published["zzz_demo"]
    info = backup._change_info(None, "zzz_demo", prev, None, None)
    assert info["version"] is None
    assert info["missing"] == ["bump", "description"]
    info = backup._change_info(None, "zzz_demo", prev, {"zzz_demo": "Fixed."},
                               {"zzz_demo": "major"})
    assert (info["version"], info["notes"], info["missing"]) == ("2.0", "Fixed.", [])
    with pytest.raises(ValueError):
        backup._change_info(None, "zzz_demo", prev, "Fixed.", "patch")
    # resuming an interrupted upload of the same content reuses its arguments
    attempts["zzz_demo"] = {"status": "awaiting_quota", "source_md5s": {"a": "1"},
                            "bump": "minor", "notes": "Fixed."}
    info = backup._change_info(None, "zzz_demo", prev, None, None, {"a": "1"})
    assert (info["version"], info["notes"], info["missing"]) == ("1.5", "Fixed.", [])
    info = backup._change_info(None, "zzz_demo", prev, None, None, {"a": "2"})
    assert info["missing"] == ["bump", "description"]
    with pytest.raises(ValueError, match=r"zzz_demo \(bump, description\)"):
        backup.require_change_info(None, ["zzz_demo", "zzz_other", "zzz_skip"],
                                   None, None, config=prod_config(tmp_path))
    backup.require_change_info(None, ["zzz_demo", "zzz_other"], "Fixed.", "minor",
                               config=prod_config(tmp_path))


def test_backup_plan(offline_backup, tmp_path):
    backup, published, attempts = offline_backup
    make_dump(tmp_path / "dump", "zzz_demo")
    make_dump(tmp_path / "dump", "zzz_other")
    cfg = prod_config(tmp_path)
    plan = backup.backup_folder(None, tmp_path / "dump", config=cfg,
                                description="Added rows.", bump="minor")
    assert plan["version"] == "2.3"
    items = {item["table"]: item for item in plan["upload"]}
    assert items["zzz_demo"]["previous_version"] == "1.4"
    assert items["zzz_demo"]["version"] == "1.5"
    assert items["zzz_demo"]["notes"] == "Added rows."
    assert items["zzz_other"]["version"] == "1.0"
    assert items["zzz_other"]["first_version"]
    # a live run refuses to start without the change information
    with pytest.raises(ValueError, match="zzz_demo"):
        backup.backup_folder(None, tmp_path / "dump", config=cfg,
                             dry_run=False)


######################################################################
# upload retries, deploy ordering, backfill retries                  #
######################################################################

class _Response:
    def __init__(self, status, payload=None):
        self.status_code = status
        self.headers = {}
        self._payload = payload or {}
        self.content = json.dumps(self._payload).encode()
        self.text = self.content.decode()

    def json(self):
        return self._payload


def test_upload_retry_resends_whole_file(tmp_path, monkeypatch):
    pytest.importorskip("requests")
    import time
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    payload = b"payload" * 1000
    path = tmp_path / "zzz_demo.txt.zst"
    path.write_bytes(payload)
    bodies = []

    class Session:
        def request(self, method, url, data=None, **kwds):
            bodies.append(data.read())
            if len(bodies) == 1:
                return _Response(503)
            return _Response(200, {"checksum": "md5:" + hashlib.md5(payload).hexdigest()})

    client = ZenodoClient("fake-token", live=True, min_interval=0, log=lambda msg: None)
    client._session = Session()
    client.upload_file("https://example.org/bucket", path)
    assert bodies == [payload, payload]


def test_quota_response_is_classified(tmp_path):
    pytest.importorskip("requests")
    from lmfdb.zenodo.client import QuotaExceeded, ZenodoError
    path = tmp_path / "zzz_demo.txt.zst"
    path.write_bytes(b"payload")
    message = {}

    class Session:
        def request(self, method, url, data=None, **kwds):
            return _Response(400, {"status": 400, "message": message["text"]})

    client = ZenodoClient("fake-token", live=True, min_interval=0, log=lambda msg: None)
    client._session = Session()
    # what Zenodo returns for an upload beyond the record's remaining quota
    message["text"] = "File size limit exceeded."
    with pytest.raises(QuotaExceeded):
        client.upload_file("https://example.org/bucket", path)
    message["text"] = "Validation error."
    with pytest.raises(ZenodoError) as err:
        client.upload_file("https://example.org/bucket", path)
    assert type(err.value) is ZenodoError


def test_major_at_commit(monkeypatch):
    requests = pytest.importorskip("requests")
    from lmfdb.zenodo import watcher

    class Resp:
        def __init__(self, status, text=""):
            self.status_code, self.text = status, text

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(str(self.status_code))

    responses = {"a": Resp(200, "MAJOR = 3\n"), "b": Resp(404), "c": Resp(503),
                 "d": Resp(200, "LEGACY_VERSION = 'x'\n")}
    monkeypatch.setattr(requests, "get",
                        lambda url, timeout: responses[url.split("/")[-3]])
    assert watcher.major_at_commit("a", 2) == 3
    assert watcher.major_at_commit("b", 2) == 2  # predates lmfdb/version.py
    with pytest.raises(requests.HTTPError):  # never guess on a transient error
        watcher.major_at_commit("c", 2)
    with pytest.raises(ValueError):
        watcher.major_at_commit("d", 2)


def test_readme_lists_columns():
    from types import SimpleNamespace
    # the interface of psycodict 1.0's search tables (no extra_cols)
    table = SimpleNamespace(
        search_cols=["label", "dim"],
        col_type={"id": "bigint", "label": "text", "dim": "integer"},
        description=lambda: "A test table",
        column_description=lambda: {"label": "The label", "dim": "The dimension"},
        stats=SimpleNamespace(quick_count=lambda query: 1))
    db = {"zzz_demo": table}
    assert metadata._table_info(db, "zzz_demo") == ("A test table", [
        ("id", "bigint", ""), ("label", "text", "The label"),
        ("dim", "integer", "The dimension")], 1)
    assert "| `dim` | `integer` | The dimension |" in metadata.table_readme(
        db, "zzz_demo", "1.0")


def test_record_deploy_ignores_superseded_commits(monkeypatch):
    pytest.importorskip("psycodict")
    from types import SimpleNamespace
    from lmfdb.zenodo import state, watcher
    calls = []
    monkeypatch.setattr(state, "latest_versions", lambda db: {
        "major": 2, "data_seq": 0, "code_seq": 1, "time": None})
    monkeypatch.setattr(state, "code_rows_for_commit", lambda db, commit: [
        r for rows in calls for r in rows if r["git_hash"] == commit])
    monkeypatch.setattr(state, "insert_version_rows", lambda db, rows: calls.append(rows))
    cfg = SimpleNamespace(editor=None, grace_dsn=None, sandbox=False)
    b, c, d = "b" * 40, "c" * 40, "d" * 40
    # B's workflow failed, C was pushed and recorded, then B is rerun
    assert watcher.record_deploy(None, b, major=2, config=cfg, head=c) is None
    event = watcher.record_deploy(None, c, major=2, config=cfg, head=c)
    assert (event["kind"], event["seq"]) == ("code", 2)
    assert watcher.record_deploy(None, c, major=2, config=cfg, head=c) is None
    assert len(calls) == 1
    # a major bump writes its two rows in a single statement
    watcher.record_deploy(None, d, major=3, config=cfg, head=d)
    assert [(r["kind"], r["major"], r["seq"]) for r in calls[-1]] == [
        ("major", 3, 3), ("code", 3, 0)]


def test_backfill_retries(offline_backup, tmp_path, monkeypatch):
    backup, published, attempts = offline_backup
    published.clear()
    names = ["zzz_a", "zzz_b", "zzz_c"]
    monkeypatch.setattr(backup, "load_tables_yaml", lambda path=None: {
        t: {"backup": "yes"} for t in names})
    dumped, uploaded, finalized = [], [], []
    fail, pause = {"zzz_b"}, {"zzz_c"}

    class DB:
        tablenames = names

        def table_sizes(self):
            return {t: {"table_bytes": i} for i, t in enumerate(names)}

        def copy_to(self, tables, folder):
            folder.mkdir(parents=True)  # like psycodict, refuses an existing folder
            for t in tables:
                make_dump(folder, t)
            dumped.extend(tables)

    def fake_backup_folder(db, folder, tables, **kwds):
        (t,) = tables
        assert (folder / (t + ".txt")).exists()
        if t in fail:
            fail.discard(t)
            raise RuntimeError("network down")
        if t in pause:
            pause.discard(t)
            return {"paused": [t]}
        published[t] = {"version": "1.0", "source_md5s": {}, "owner": "roed"}
        uploaded.append(t)
        return {"paused": []}

    monkeypatch.setattr(backup, "backup_folder", fake_backup_folder)
    monkeypatch.setattr(backup, "finalize",
                        lambda db, **kwds: finalized.append(1) or "2.1")
    cfg = prod_config(tmp_path)
    root = tmp_path / "staging" / "backfill"
    with pytest.raises(RuntimeError):
        backup.backfill(DB(), dry_run=False, config=cfg)
    assert (dumped, uploaded) == (["zzz_a", "zzz_b"], ["zzz_a"])
    # an interrupted dump of zzz_c is redone, not reused
    (root / "zzz_c").mkdir()
    (root / "zzz_c" / "zzz_c.txt").write_text("partial")
    # zzz_b's completed dump is reused; zzz_c pauses for quota
    assert backup.backfill(DB(), dry_run=False, config=cfg) is None
    assert dumped == ["zzz_a", "zzz_b", "zzz_c"] and not finalized
    assert [p.name for p in root.iterdir()] == ["zzz_c"]
    assert backup.backfill(DB(), dry_run=False, config=cfg) == "2.1"
    assert dumped == ["zzz_a", "zzz_b", "zzz_c"] and finalized == [1]
    assert uploaded == names and not list(root.iterdir())


######################################################################
# against a scratch PostgreSQL database (opt-in)                     #
######################################################################
# Set LMFDB_ZENODO_TEST_DB to a libpq connection string for a disposable
# database, e.g. "host=127.0.0.1 port=5439 dbname=zenodo_test user=postgres":
# these tests drop and recreate the archive state and knowl tables there.

KNOWL_DDL = {
    "kwl_knowls": "id text, cat text, title text, content text, last_author text, "
                  "timestamp timestamp, status smallint, type smallint, links text[], "
                  "defines text[], source text, source_name text, reviewer text, "
                  "reviewer_timestamp timestamp, authors text[], _keywords text[]",
    "kwl_deleted": "id text, cat text, title text, content text, authors jsonb, "
                   "last_author text, quality text, timestamp timestamp, "
                   "_keywords jsonb, history jsonb",
}


@pytest.fixture
def scratch_db(tmp_path):
    dsn = os.environ.get("LMFDB_ZENODO_TEST_DB")
    if not dsn:
        pytest.skip("LMFDB_ZENODO_TEST_DB not set")
    from psycopg.conninfo import conninfo_to_dict
    from psycodict import SQL
    from psycodict.database import PostgresDatabase
    from psycodict.config import Configuration
    config = Configuration(readargs=False,
                           defaults={"config_file": str(tmp_path / "psycodict.ini")})
    db = PostgresDatabase(config=config, create=True, **conninfo_to_dict(dsn))
    db._execute(SQL("CREATE SCHEMA IF NOT EXISTS userdb"))
    for t in ["version_history", "userdb.zenodo_backups", "kwl_knowls", "kwl_deleted",
              "userdb.dbrecord",
              "userdb.version_history_sandbox", "userdb.zenodo_backups_sandbox"]:
        db._execute(SQL("DROP TABLE IF EXISTS " + t))
    for t, cols in KNOWL_DDL.items():
        db._execute(SQL("CREATE TABLE %s (%s)" % (t, cols)))
    db._execute(SQL(
        "INSERT INTO kwl_knowls (id, title, content, timestamp, status, links, "
        "authors) VALUES (%s, %s, %s, '2026-11-16 12:00', 1, %s::text[], "
        "%s::text[]), (%s, %s, NULL, '2026-11-16 12:01', 0, NULL, '{}')"),
        ["ec.rank", "Rank | of E", "line one\nline\ttwo \\ backslash",
         '{"ec.conductor","a,b|c"}', '{"Ann O\'Nymous"}',
         "nf.degree", "Degree"])
    db._execute(SQL(
        "INSERT INTO kwl_deleted (id, authors, timestamp, history) VALUES "
        "(%s, %s::jsonb, '2026-11-16 12:02', %s::jsonb)"),
        ["old.knowl", '["x", "y|z"]', '[{"rev": 1}]'])
    yield db
    db.conn.close()


def test_knowls_dump_restores(scratch_db, tmp_path):
    from psycodict import SQL, Identifier
    db = scratch_db
    dump = tmp_path / "dump"
    packaging.dump_knowls(db, dump)
    header = (dump / "kwl_knowls.txt").read_text().split("\n")[1].split("|")
    assert "text[]" in header and "ARRAY" not in header
    # restore following the README: run the schema files, then COPY the data
    # (minus the three header lines) into the new tables
    db._execute(SQL("DROP SCHEMA IF EXISTS restored CASCADE"))
    db._execute(SQL("CREATE SCHEMA restored"))
    for t in packaging.KNOWL_TABLES:
        db._execute(SQL("SET search_path TO restored"))
        db._execute(SQL((dump / (t + "_schema.sql")).read_text()))
        db._execute(SQL("SET search_path TO public"))
        data = (dump / (t + ".txt")).read_text().split("\n", 3)[3]
        cur = db._cursor()
        with cur.copy(SQL("COPY restored.{0} FROM STDIN (DELIMITER '|')").format(
                Identifier(t))) as copy:
            copy.write(data)
        db.conn.commit()
        rows = [db._execute(SQL("SELECT * FROM %s.%s ORDER BY id" % (schema, t))).fetchall()
                for schema in ["public", "restored"]]
        assert rows[0] == rows[1] and rows[0]
    db._execute(SQL("DROP SCHEMA restored CASCADE"))
    # an unchanged knowl database dumps identically
    again = tmp_path / "again"
    packaging.dump_knowls(db, again)
    assert (again / "kwl_knowls.txt").read_bytes() == (dump / "kwl_knowls.txt").read_bytes()


def test_sandbox_state_is_separate(scratch_db, tmp_path, monkeypatch):
    from lmfdb.zenodo import backup, state
    db = scratch_db
    monkeypatch.setattr(backup, "_current_major", lambda: 2)
    state.ensure_tables(db)
    state.insert_major(db, 2, comment="activated")
    sandbox = ZenodoConfig(path=str(tmp_path / "missing.ini"))
    assert sandbox.sandbox
    sdb = backup._state_db(db, sandbox)
    aid = state.start_attempt(sdb, "nf_fields", "roed", "1.0", {})
    state.update_attempt(sdb, aid, status="verified", recid="1")
    state.insert_version_rows(sdb, [state.version_row(2, "data", 1, tables={})])
    assert state.latest_published(backup._state_db(db, sandbox), "nf_fields")["recid"] == "1"
    assert state.latest_published(db, "nf_fields") is None
    assert state.current_version_string(db) == "2.0-0"
    # the production backfill still has nf_fields to do
    assert backup.backfill(db, tables=["nf_fields"], config=prod_config(tmp_path)) == ["nf_fields"]


def test_major_rows_land_together(scratch_db):
    from lmfdb.zenodo import state
    db = scratch_db
    state.ensure_tables(db)
    state.insert_version_rows(db, [state.version_row(3, "code", 0, git_hash="x")])
    with pytest.raises(Exception):  # the code row collides, so neither lands
        state.insert_major(db, 3, git_hash="y")
    assert not [r for r in state.history(db) if r["kind"] == "major"]


class FakeZenodo:
    """
    In-memory stand-in for ZenodoClient.  Uploads for ``blocked`` tables get
    Zenodo's over-quota response, classified by the real client; published
    depositions refuse edits; ``lose_publish_response`` makes the next
    publication succeed but its response fail.
    """

    def __init__(self):
        self.deps, self.next_id, self.blocked = {}, 100, set()
        self.lose_publish_response = False

    def _new(self, files=None, concept=None):
        dep_id = self.next_id
        self.next_id += 1
        self.deps[dep_id] = {"id": dep_id, "files": dict(files or {}),
                             "concept": concept or dep_id, "metadata": {},
                             "submitted": False, "state": "unsubmitted",
                             "links": {"bucket": "bucket/%s" % dep_id}}
        return self.deps[dep_id]

    def create_deposition(self, metadata=None):
        return self._new()

    def get_deposition(self, dep_id):
        return self.deps[int(dep_id)]

    def new_version(self, recid):
        prev = self.deps[int(recid)]
        return self._new(prev["files"], prev["concept"])

    def update_metadata(self, dep_id, metadata):
        from lmfdb.zenodo.client import ZenodoError
        dep = self.deps[int(dep_id)]
        if dep["submitted"]:
            raise ZenodoError("published depositions cannot be edited")
        dep["metadata"] = metadata["metadata"]

    def list_files(self, dep_id):
        return [{"filename": name, "checksum": "md5:" + md5,
                 "links": {"self": (int(dep_id), name)}}
                for name, md5 in self.deps[int(dep_id)]["files"].items()]

    def delete_file(self, link):
        del self.deps[link[0]]["files"][link[1]]

    def upload_file(self, bucket, path, name=None):
        dep = self.deps[int(bucket.split("/")[1])]
        if dep["metadata"].get("title", "").split()[-1] in self.blocked:
            over = {"status": 400, "message": "File size limit exceeded."}

            class Session:
                def request(self, method, url, **kwds):
                    return _Response(400, over)

            client = ZenodoClient("fake-token", live=True, min_interval=0,
                                  log=lambda msg: None)
            client._session = Session()
            return client.upload_file(bucket, path, name=name)
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        dep["files"][name] = md5
        return {"checksum": "md5:" + md5}

    def publish(self, dep_id):
        dep = self.deps[int(dep_id)]
        dep.update(submitted=True, state="done", doi="10.5072/zenodo.%s" % dep["id"],
                   conceptrecid=dep["concept"],
                   conceptdoi="10.5072/zenodo.%s" % dep["concept"])
        if self.lose_publish_response:
            self.lose_publish_response = False
            raise ConnectionError("connection reset after publishing")
        return {k: dep[k] for k in ["id", "doi", "conceptrecid", "conceptdoi"]}

    def verify_record(self, recid, local_md5s):
        return []


def push_setup(db, tmp_path, monkeypatch):
    """A production archive at version 2.0 of tables zzz_a, zzz_b, on a fake Zenodo."""
    from lmfdb.zenodo import backup, state
    fake = FakeZenodo()
    monkeypatch.setattr(backup, "ZenodoClient", lambda *args, **kwds: fake)
    monkeypatch.setattr(backup, "_current_major", lambda: 2)
    monkeypatch.setattr(backup, "load_tables_yaml", lambda path=None: {
        "zzz_a": {"backup": "yes"}, "zzz_b": {"backup": "yes"}})
    state.ensure_tables(db)
    state.insert_major(db, 2)
    return backup, state, fake, prod_config(tmp_path, enabled=True)


def test_push_waits_for_paused_upload(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    for t in ["zzz_a", "zzz_b"]:
        make_dump(tmp_path / "push1", t)
        make_dump(tmp_path / "push2", t, nrows=30)
    plan = backup.backup_folder(db, tmp_path / "push1", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.1"
    # both tables change; zzz_b needs more quota than its owner has
    fake.blocked.add("zzz_b")
    plan = backup.backup_folder(db, tmp_path / "push2", dry_run=False, live=True,
                                config=cfg, description="More rows.", bump="minor")
    assert plan["paused"] == ["zzz_b"] and plan["version"] is None
    assert state.current_version_string(db) == "2.1-0"
    with pytest.raises(RuntimeError):
        backup.finalize(db, cfg=cfg, live=True)
    # once the quota is raised, re-running completes the push as one version
    fake.blocked.clear()
    plan = backup.backup_folder(db, tmp_path / "push2", dry_run=False, live=True,
                                config=cfg)
    assert plan["skip_unchanged"] == ["zzz_a"] and plan["version"] == "2.2"
    tables = state.resolve_version(db, 2, 2)["tables"]
    assert tables["zzz_a"]["version"] == tables["zzz_b"]["version"] == "1.1"
    assert tables["zzz_b"]["notes"] == "More rows."
    assert [r["seq"] for r in state.history(db) if r["kind"] == "data"] == [2, 1]


def test_newer_dump_supersedes_paused_attempt(scratch_db, tmp_path, monkeypatch):
    from psycodict import SQL
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "v1", "zzz_a")
    make_dump(tmp_path / "v2", "zzz_a", nrows=30)
    fake.blocked.add("zzz_a")
    plan = backup.backup_folder(db, tmp_path / "v1", dry_run=False, live=True,
                                config=cfg)
    assert plan["paused"] == ["zzz_a"]
    # a corrected dump replaces the paused one before its quota is raised
    fake.blocked.clear()
    plan = backup.backup_folder(db, tmp_path / "v2", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.1"
    rows = state._backup_rows(db, SQL(" WHERE tablename = 'zzz_a' ORDER BY id"), None)
    assert [r["status"] for r in rows] == ["superseded", "verified"]
    assert rows[1]["recid"] == rows[0]["draft_id"]  # the paused draft was reused


def test_lost_publish_response_is_recovered(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")
    fake.lose_publish_response = True
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                             config=cfg)
    row = state.latest_attempt(db, "zzz_a")
    assert row["status"] == "uploading" and row["draft_id"]
    draft = row["draft_id"]
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.1"
    row = state.latest_attempt(db, "zzz_a")
    assert (row["status"], row["recid"]) == ("verified", draft)


def test_audit_compares_with_snapshot_time(scratch_db, tmp_path, monkeypatch):
    from datetime import datetime
    from psycodict import SQL
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    db._execute(SQL("CREATE TABLE userdb.dbrecord "
                    "(tablename text, operation text, time timestamp)"))
    db.tablenames = ["zzz_a"]
    # dumped at 12:00, production reloaded at 12:05, upload finished at 12:10
    aid = state.start_attempt(db, "zzz_a", "roe", "1.0", {},
                              source_time=datetime(2026, 11, 16, 12, 0))
    state.update_attempt(db, aid, status="verified",
                         finished=datetime(2026, 11, 16, 12, 10))
    db._execute(SQL("INSERT INTO userdb.dbrecord VALUES "
                    "('zzz_a', 'reload', '2026-11-16 12:05')"))
    assert backup.audit(db, config=cfg)["changed_since_archive"] == ["zzz_a"]
