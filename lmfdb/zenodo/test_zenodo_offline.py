"""
Offline tests for the Zenodo backup system: no database, no network, no sage
required (tests comparing against sage are skipped when it is absent).
"""

import contextlib
import gzip
import hashlib
import json
import os

import pytest

from lmfdb.zenodo.versioning import (
    format_time,
    format_version,
    history_events,
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


def test_format_time():
    from datetime import datetime
    assert format_time(datetime(2026, 11, 17, 19, 3, 59, 499999)) == "2026-11-17 19:03:59 UTC"
    assert format_time(datetime(2026, 12, 31, 23, 59, 59, 500000)) == "2027-01-01 00:00:00 UTC"
    assert format_time(None) == ""


def test_history_events():
    from datetime import datetime

    def row(id, kind, major, seq, minute, git_hash=None, tables=None):
        return dict(id=id, kind=kind, major=major, seq=seq, git_hash=git_hash,
                    time=datetime(2026, 11, 17, 12, minute), tables=tables,
                    editor=None, comment=None)
    rows = [row(1, "major", 2, 2, 0, "aaa"), row(2, "code", 2, 0, 0, "aaa"),
            row(3, "data", 2, 1, 5, tables={"zzz_a": {"version": "1.0"}}),
            row(4, "code", 2, 1, 7, "bbb"), row(5, "data", 2, 2, 9),
            row(6, "major", 3, 3, 11, "ccc"), row(7, "code", 3, 0, 11, "ccc")]
    events = history_events(rows[::-1])
    assert [(e["version"], e["kind"]) for e in events] == [
        ("3.0-0", "major"), ("2.2-1", "data"), ("2.1-1", "code"),
        ("2.1-0", "data"), ("2.0-0", "major")]
    assert events[0]["git_hash"] == "ccc"
    assert events[-1]["kind_label"] == "major version bump"
    assert history_events([]) == []


def test_current_version_string_raises_on_database_errors():
    from lmfdb.zenodo import state

    class Down:
        def _execute(self, query, values=None):
            raise OSError("connection refused")
    with pytest.raises(OSError):
        state.current_version_string(Down())


######################################################################
# packaging                                                          #
######################################################################

SEP = "|"


def make_dump(folder, name="zzz_demo", nrows=20):
    """A minimal but format-faithful psycodict dump folder."""
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / (name + ".txt"), "w") as F:
        F.write(SEP.join(["id", "label", "dim"]) + "\n")
        F.write(SEP.join(["bigint", "text", "integer"]) + "\n\n")
        for i in range(nrows):
            F.write(SEP.join([str(i), "lab.%s" % i, str(i * i)]) + "\n")
    for end, rows in [("_counts.txt", 2), ("_stats.txt", 1),
                      ("_indexes.txt", 1), ("_constraints.txt", 0),
                      ("_meta.txt", 1)]:
        with open(folder / (name + end), "w") as F:
            for i in range(rows):
                F.write("row%s%sdata\n" % (i, SEP))
    return name


def test_discover_and_table_files(tmp_path):
    make_dump(tmp_path / "dump", "zzz_demo")
    make_dump(tmp_path / "dump", "zzz_other")
    assert packaging.discover_tables(tmp_path / "dump") == ["zzz_demo",
                                                            "zzz_other"]
    files = packaging.table_files(tmp_path / "dump", "zzz_demo")
    assert [f.name for f in files] == [
        "zzz_demo.txt", "zzz_demo_counts.txt",
        "zzz_demo_stats.txt", "zzz_demo_indexes.txt",
        "zzz_demo_constraints.txt", "zzz_demo_meta.txt"]
    # psycodict 1.0 has no extras tables: a leftover extras file is not part
    # of zzz_demo's record, and reload_all would call it a table of its own
    (tmp_path / "dump" / "zzz_demo_extras.txt").write_text("id\nbigint\n\n")
    assert "zzz_demo_extras" in packaging.discover_tables(tmp_path / "dump")
    assert len(packaging.table_files(tmp_path / "dump", "zzz_demo")) == 6
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
        dump, name, staging, force_gzip=True,
        readme="# test readme\n", record_version="1.4")
    outdir = staging / name

    # sources: all six files hashed, with correct row counts
    assert set(manifest["source_files"]) == {
        name + end for end in ["", "_counts", "_stats", "_indexes",
                               "_constraints", "_meta"]
        for end in [end + ".txt"]}
    assert manifest["source_files"][name + ".txt"]["rows"] == 50
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
    assert "lmfdb_version" not in manifest
    assert manifest["record_version"] == "1.4"

    # upload order: README, sample, MANIFEST, then artifacts
    names = [p.name for p in packaging.upload_list(outdir)]
    assert names[:3] == ["README.md", name + "_sample.md", "MANIFEST.json"]


def test_package_reuses_an_earlier_package(tmp_path, monkeypatch):
    dump = tmp_path / "dump"
    name = make_dump(dump, nrows=50)
    staging, outdir = tmp_path / "staging", tmp_path / "staging" / name
    # 100-byte parts, so that the search file's artifact is split
    first = packaging.package_table(dump, name, staging, force_gzip=True,
                                    chunk_gb=1e-7, readme="# v1\n",
                                    record_version="1.0")
    (outdir / "stray.txt").write_text("left over")
    calls = []
    real = packaging.compress_file
    monkeypatch.setattr(packaging, "compress_file",
                        lambda *args, **kwds: calls.append(args) or real(*args, **kwds))

    second = packaging.package_table(dump, name, staging, force_gzip=True,
                                     chunk_gb=1e-7, readme="# v2\n",
                                     record_version="1.1",
                                     source_md5s=packaging.source_md5s(dump, name))
    assert not calls
    assert second["artifacts"] == first["artifacts"]
    assert second["record_version"] == "1.1"
    assert (outdir / "README.md").read_text() == "# v2\n"
    assert not (outdir / "stray.txt").exists()
    assert json.loads((outdir / "MANIFEST.json").read_text()) == second

    # packaged again after losing a part, with another chunk size, or for
    # changed sources
    parts = [p for art in second["artifacts"] for p in art.get("parts", [])]
    assert parts
    (outdir / parts[0]["name"]).unlink()
    packaging.package_table(dump, name, staging, force_gzip=True, chunk_gb=1e-7)
    assert len(calls) == 6
    packaging.package_table(dump, name, staging, force_gzip=True)
    assert len(calls) == 12
    with open(dump / (name + ".txt"), "a") as F:
        F.write("50|lab.50|2500\n")
    third = packaging.package_table(dump, name, staging, force_gzip=True)
    assert len(calls) == 18
    assert third["source_files"][name + ".txt"]["rows"] == 51


def test_gzip_output_is_reproducible(tmp_path, monkeypatch):
    import itertools
    from types import SimpleNamespace
    src = tmp_path / "t.txt"
    src.write_text("1|2\n" * 1000)
    clock = itertools.count(10**9, 10**9)
    monkeypatch.setattr(gzip, "time", SimpleNamespace(time=lambda: next(clock)))
    out = []
    for d in ["a", "b"]:
        (tmp_path / d).mkdir()
        out.append(packaging.compress_file(src, tmp_path / d,
                                           force_gzip=True).read_bytes())
    assert out[0] == out[1]
    assert gzip.decompress(out[0]) == src.read_bytes()


def test_sample_shows_a_row_by_field(tmp_path):
    name = make_dump(tmp_path / "dump", nrows=5)
    src = tmp_path / "dump" / (name + ".txt")
    packaging.write_sample(src, tmp_path / "s.md")
    text = (tmp_path / "s.md").read_text()
    assert "The first row, field by field" in text
    assert "| `label` | `text` | lab.0 |" in text
    assert "    0|lab.0|0" in text and "    4|lab.4|16" in text
    packaging.write_sample(src, tmp_path / "t.md", keep=lambda r: r["dim"] == "9",
                           chosen="the rows of dimension 9")
    text = (tmp_path / "t.md").read_text()
    assert "The first of the rows of dimension 9" in text
    assert "| `label` | `text` | lab.3 |" in text and "lab.4" not in text
    assert packaging.copy_fields("a|b\\|c|\\N") == ["a", "b\\|c", "\\N"]


def test_shown_knowls(tmp_path):
    dump = tmp_path / "kwl_knowls.txt"
    dump.write_text("id|status|timestamp|content\ntext|smallint|timestamp|text\n\n"
                    "a.b|1|2026-01-01 00:00:00|old\n"
                    "a.b|1|2026-02-01 00:00:00|reviewed\n"
                    "a.b|0|2026-03-01 00:00:00|beta\n"
                    "c.d|-2|2026-03-01 00:00:00|deleted\n")
    assert packaging.shown_knowls(dump) == {("a.b", "2026-02-01 00:00:00")}


def test_split_refuses_empty_parts(tmp_path):
    path = tmp_path / "x.zst"
    path.write_bytes(b"data")
    for size in [0, -1]:
        with pytest.raises(ValueError):
            packaging.split_file(path, size)
    assert path.read_bytes() == b"data"


def test_split_and_reassemble(tmp_path):
    dump = tmp_path / "dump"
    name = make_dump(dump, nrows=2000)
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
    name = make_dump(dump, nrows=30)
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
    assert after[name + "_counts.txt"] == before[name + "_counts.txt"]


######################################################################
# metadata                                                           #
######################################################################

def test_metadata_without_db(tmp_path):
    notes = "Added <weight 1> forms & fixed labels."
    desc = metadata.table_description_html(None, "zzz_demo", "1.4", nrows=17,
                                           notes=notes)
    assert "zzz_demo" in desc and "17" in desc
    assert "Version 1.4 of" in desc and "lmfdb.org/version" in desc
    assert "Added &lt;weight 1&gt; forms &amp; fixed labels." in desc
    # the README is written once the files are packaged, and lists them
    name = make_dump(tmp_path / "dump")
    packaging.package_table(
        tmp_path / "dump", name, tmp_path / "staging", force_gzip=True,
        readme=lambda manifest: metadata.table_readme(
            None, name, "1.4", manifest, notes=notes, psycodict_version="1.0.0"))
    readme = (tmp_path / "staging" / name / "README.md").read_text()
    assert readme.startswith("# LMFDB table zzz_demo, version 1.4")
    assert "lmfdb.org/version" in readme
    assert "Changes in this version: " + notes in readme
    assert "| `zzz_demo.txt.gz` |" in readme and "**the data**" in readme
    assert "| `zzz_demo_sample.md` |" in readme and "`\\N` is NULL" in readme
    assert "reload_all" in readme and "psycodict 1.0.0" in readme
    md = metadata.deposit_metadata(
        metadata.table_title(None, "zzz_demo"), desc, "1.4",
        related=[("https://www.lmfdb.org/api/zzz_demo", "isSupplementTo")],
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

def test_config_defaults_and_parsing(tmp_path, monkeypatch):
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
    # a part size of 0 would split every file into nothing
    bad = tmp_path / "bad.ini"
    bad.write_text("[zenodo]\nchunk_gb = 0\n")
    os.chmod(bad, 0o600)
    with pytest.raises(ValueError, match="chunk_gb"):
        ZenodoConfig(path=str(bad))
    # set from Python, e.g. in a Sage session, the variable keeps its ~
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LMFDB_ZENODO_CONFIG", "~/zenodo.ini")
    assert ZenodoConfig().enabled


######################################################################
# tables.yaml / eligibility (needs psycodict only for module import)  #
######################################################################

def test_tables_yaml():
    pytest.importorskip("psycodict")
    from lmfdb.zenodo.backup import load_tables_yaml, classify
    spec = load_tables_yaml()
    assert all(e["backup"] in ("yes", "no", "hold", "review") for e in spec.values())
    assert all(e.get("owner") for e in spec.values() if e["backup"] in ("yes", "hold"))
    assert spec["nf_fields"]["backup"] == "yes"
    assert spec["gps_groups_test"]["backup"] == "no"
    split = classify(["nf_fields", "gps_groups_test", "lfunc_lfunctions",
                      "totally_new_table"], spec)
    assert split == {"yes": ["nf_fields"], "no": ["gps_groups_test"],
                     "hold": ["lfunc_lfunctions"], "review": [],
                     "unlisted": ["totally_new_table"]}


######################################################################
# change requests from GitHub issues                                 #
######################################################################

FORM_BODY = """### Tables

- `mf_newforms`
- mf_hecke_traces, mf_hecke_cc

### Description of the change

Added newforms of weight 1.

### Version update

minor

### Per-table details (optional)

_No response_

### Checks

- [X] I have checked the pages that use this data on beta.lmfdb.org.
"""


def issue_json(body, state="open"):
    return {"html_url": "https://github.com/LMFDB/lmfdb/issues/7123",
            "title": "[Data to prod] newforms", "state": state,
            "user": {"login": "someone"}, "updated_at": "2026-11-16T12:00:00Z",
            "body": body}


def test_change_request_from_issue():
    from lmfdb.zenodo.issues import change_request, summary
    req = change_request(issue_json(FORM_BODY.replace("\n", "\r\n")))
    assert req["tables"] == ["mf_newforms", "mf_hecke_traces", "mf_hecke_cc"]
    assert (req["description"], req["bump"]) == ("Added newforms of weight 1.", "minor")
    # per-table details override the form's description and version update
    body = FORM_BODY.replace(
        "minor\n\n### Per", "different for different tables (explain below)\n\n### Per"
    ).replace("_No response_", "mf_newforms: major, Relabeled.\n"
              "mf_hecke_traces: minor\nmf_hecke_cc: Minor")
    req = change_request(issue_json(body))
    assert req["bump"] == {"mf_newforms": "major", "mf_hecke_traces": "minor",
                           "mf_hecke_cc": "minor"}
    assert req["description"]["mf_newforms"] == "Relabeled."
    assert req["description"]["mf_hecke_cc"] == "Added newforms of weight 1."
    assert "major: Relabeled." in summary(req)
    # anything ambiguous is refused rather than guessed
    for bad in [body.replace("mf_hecke_cc: Minor", ""),
                body.replace("mf_hecke_cc: Minor", "and please check cc"),
                body.replace("mf_hecke_cc: Minor", "mf_other: minor"),
                FORM_BODY.replace("mf_hecke_cc", "mf_hecke_cc; drop"),
                FORM_BODY.replace("\nminor\n", "\npatch\n"),
                "Please copy mf_newforms"]:
        with pytest.raises(ValueError):
            change_request(issue_json(bad))
    with pytest.raises(ValueError, match="closed"):
        change_request(issue_json(FORM_BODY, state="closed"))


def test_issue_form_labels():
    yaml = pytest.importorskip("yaml")
    from pathlib import Path
    from lmfdb.zenodo import issues
    path = (Path(__file__).resolve().parents[2] / ".github" / "ISSUE_TEMPLATE"
            / "data-to-prod.yml")
    if not path.exists():
        pytest.skip("not in a git checkout")
    fields = {f["id"]: f["attributes"] for f in yaml.safe_load(path.read_text())["body"]
              if "id" in f}
    assert [fields[k]["label"] for k in ["tables", "description", "bump", "per_table"]] == [
        issues.TABLES, issues.DESCRIPTION, issues.BUMP, issues.PER_TABLE]
    options = fields["bump"]["options"]
    assert options[:2] == ["minor", "major"] and options[2].startswith("different")


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
                              "owner": "roed", "status": "verified"}}
    attempts = {}
    monkeypatch.setattr(backup, "load_tables_yaml", lambda path=None: {
        "zzz_demo": {"backup": "yes"}, "zzz_other": {"backup": "yes"},
        "zzz_skip": {"backup": "no"}})
    monkeypatch.setattr(backup, "_current_major", lambda: 2)
    monkeypatch.setattr(state, "latest_published",
                        lambda db, name: published.get(name))
    monkeypatch.setattr(state, "latest_attempt",
                        lambda db, name, statuses=None: attempts.get(name))
    monkeypatch.setattr(state, "next_data_version", lambda db: (2, 3))
    monkeypatch.setattr(state, "unfinished", lambda db: [])
    monkeypatch.setattr(state, "lock", lambda db: contextlib.nullcontext())
    monkeypatch.setattr(state, "add_missing_columns", lambda db: None)
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
    # a live run refuses to start while disabled, or without the change
    # information
    with pytest.raises(RuntimeError, match="disabled"):
        backup.backup_folder(None, tmp_path / "dump", config=cfg,
                             dry_run=False)
    with pytest.raises(ValueError, match="zzz_demo"):
        backup.backup_folder(None, tmp_path / "dump", dry_run=False,
                             config=prod_config(tmp_path, enabled=True))


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


def test_guard_runs_before_every_request(monkeypatch):
    import time
    pytest.importorskip("requests")
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    responses, checks = [], []

    class Session:
        def request(self, method, url, data=None, **kwds):
            return responses.pop(0)

    def guard():
        checks.append(len(responses))
        if lock_lost:
            raise RuntimeError("lock lost")

    client = ZenodoClient("fake-token", live=True, min_interval=0,
                          log=lambda msg: None, guard=guard)
    client._session = Session()
    lock_lost = False
    responses[:] = [_Response(503), _Response(204)]
    client.delete_draft(1)
    assert checks == [2, 1]  # before the request, and again before its retry
    # the lock is lost during the backoff: the retry is not sent
    responses[:] = [_Response(503), _Response(204)]
    checks.clear()

    class LoseLock:
        def request(self, method, url, data=None, **kwds):
            nonlocal lock_lost
            lock_lost = True
            return responses.pop(0)

    client._session = LoseLock()
    lock_lost = False
    with pytest.raises(RuntimeError, match="lock lost"):
        client.delete_draft(1)
    assert len(responses) == 1


def test_new_version_reuses_an_open_draft():
    pytest.importorskip("requests")
    sent, draft_files = [], []

    class Session:
        def request(self, method, url, data=None, **kwds):
            path = url.split("/api", 1)[1]
            sent.append((method, path))
            if path == "/records/5/versions":
                return _Response(201, {"id": "7"})
            if path == "/deposit/depositions/7/files":
                return _Response(200, list(draft_files))
            if path == "/records/7/draft/actions/files-import":
                draft_files.append({"filename": "a.txt"})
                return _Response(201, {})
            return _Response(200, {"id": 7, "links": {"bucket": "b"}})

    client = ZenodoClient("fake-token", live=True, min_interval=0,
                          log=lambda msg: None)
    client._session = Session()
    importing = ("POST", "/records/7/draft/actions/files-import")
    assert client.new_version(5)["id"] == 7 and importing in sent
    # asked again (e.g. after a lost response): the same draft, imported once
    sent.clear()
    assert client.new_version(5)["id"] == 7 and importing not in sent


def test_republish_discards_a_failed_edit():
    pytest.importorskip("requests")
    from lmfdb.zenodo.client import ZenodoError
    sent = []

    class Session:
        def request(self, method, url, data=None, params=None, **kwds):
            path = url.split("/api", 1)[1]
            sent.append((method, path, params))
            if path.endswith("/actions/publish"):
                return _Response(400, {"message": "validation error"})
            if path.startswith("/communities/"):
                return _Response(200, {"hits": {"total": 1}})
            return _Response(201, {})

    client = ZenodoClient("fake-token", live=True, min_interval=0,
                          log=lambda msg: None)
    client._session = Session()
    with pytest.raises(ZenodoError):
        client.republish(7)
    assert [s[:2] for s in sent] == [
        ("POST", "/records/7/draft"), ("POST", "/records/7/draft/actions/publish"),
        ("DELETE", "/records/7/draft")]
    sent.clear()
    assert client.in_community("lmfdb", 7)
    assert sent == [("GET", "/communities/lmfdb/records", {"q": "id:7", "size": 1})]


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


def test_dropped_connection_is_retried_for_uploads(tmp_path, monkeypatch):
    requests = pytest.importorskip("requests")
    import time
    sleeps = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    payload = b"payload" * 1000
    path = tmp_path / "zzz_demo.txt.zst"
    path.write_bytes(payload)
    calls, bodies = [], []

    class Session:
        def request(self, method, url, data=None, **kwds):
            calls.append(method)
            if data is not None:
                bodies.append(data.read())
            if len(calls) == 1:
                raise requests.exceptions.SSLError(
                    "EOF occurred in violation of protocol")
            return _Response(200, {"checksum": "md5:" + hashlib.md5(payload).hexdigest()})

    client = ZenodoClient("fake-token", live=True, min_interval=0, log=lambda msg: None)
    client._session = Session()
    client.upload_file("https://example.org/bucket", path)
    assert bodies == [payload, payload] and sleeps == [30]
    # a POST is not sent again: it could create a second draft
    calls.clear()
    with pytest.raises(requests.ConnectionError):
        client.create_deposition()
    assert calls == ["POST"]


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

    # the web proxy's cap on one request, which raising the quota cannot lift
    class ProxySession:
        def request(self, method, url, data=None, **kwds):
            return _Response(413, {})

    client._session = ProxySession()
    with pytest.raises(ZenodoError, match="chunk_gb") as err:
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
        description=lambda: "Test curves over *Q*",
        column_description=lambda: {
            "label": "The {{ KNOWL('ec.label', 'label') }}", "dim": "The dimension"},
        stats=SimpleNamespace(quick_count=lambda query: 1))
    db = {"zzz_demo": table}
    assert metadata._table_info(db, "zzz_demo") == ("Test curves over *Q*", [
        ("id", "bigint", ""), ("label", "text", "The {{ KNOWL('ec.label', 'label') }}"),
        ("dim", "integer", "The dimension")], 1)
    readme = metadata.table_readme(db, "zzz_demo", "1.0",
                                   {"artifacts": [], "source_files": {}})
    assert readme.startswith("# Test curves over Q (LMFDB table zzz_demo), version 1.0")
    assert "| `dim` | `integer` | The dimension |" in readme
    # knowl references become links, on the README and on the record page
    assert "The [label](https://www.lmfdb.org/knowledge/show/ec.label) |" in readme
    page = metadata.table_description_html(db, "zzz_demo", "1.0")
    assert '<a href="https://www.lmfdb.org/knowledge/show/ec.label">label</a>' in page
    assert "<em>Q</em>" in page and "KNOWL" not in page
    assert metadata.table_keywords(db, "zzz_demo") == ["zzz_demo", "Test curves over Q"]


def test_render_knowl():
    render = metadata.render_knowl
    assert render("{{KNOWL('ag.aut_group', 'automorphism group')}}") == (
        "[automorphism group](https://www.lmfdb.org/knowledge/show/ag.aut_group)")
    assert render("{{ KNOWL_LINK('nf.degree') }}") == (
        "[nf.degree](https://www.lmfdb.org/knowledge/show/nf.degree)")
    assert render('{{ KNOWL("a.b", title="t") }}, {{ LINK_EXT("x", "https://x.org") }}, '
                  "{{ DEFINES('field') }}") == (
        "[t](https://www.lmfdb.org/knowledge/show/a.b), [x](https://x.org), **field**")
    assert render("{{ TEXT_DATA(f, p) }}") == "{{ TEXT_DATA(f, p) }}"
    html = metadata._html("over $\\mathbb{Q}_{p}$ and *a* $x_1 * y_2$")
    assert "$\\mathbb{Q}_{p}$" in html and "$x_1 * y_2$" in html and "<em>a</em>" in html


def test_sandbox_links_go_to_record_pages(tmp_path):
    pytest.importorskip("psycodict")
    from lmfdb.zenodo import backup
    entry = {"doi": "10.5072/zenodo.7", "recid": "7"}
    sandbox = ZenodoConfig(path=str(tmp_path / "missing.ini"))
    # test DOIs (10.5072) do not resolve, so the sandbox links record pages
    assert backup._record_url(sandbox)(entry) == "https://sandbox.zenodo.org/records/7"
    assert backup._record_url(prod_config(tmp_path))(entry) == "https://doi.org/10.5072/zenodo.7"
    readme = metadata.registry_readme({"lmfdb_version": "2.1", "tables": {"zzz_a": dict(
        entry, version="1.0")}}, {}, "", record_url=backup._record_url(sandbox))
    assert "[10.5072/zenodo.7](https://sandbox.zenodo.org/records/7)" in readme


def test_registry_readme():
    registry = {"lmfdb_version": "2.2", "tables": {
        "zzz_a": {"version": "1.1", "doi": "10.5281/zenodo.3", "size": 12_400_000,
                  "rows": 66158, "notes": "More rows."},
        "lmfdb_knowls": {"version": "1.0", "doi": "10.5281/zenodo.5", "notes": None}}}
    readme = metadata.registry_readme(registry, {"zzz_a": "Curves (LMFDB table zzz_a)"},
                                      "This data version includes 1 of the 2 tables.")
    assert "# LMFDB version registry, data version 2.2" in readme
    assert "data version [2.2](https://www.lmfdb.org/version?v=2.2)" in readme
    assert ("| Curves (LMFDB table zzz_a) | 1.1 | [10.5281/zenodo.3]"
            "(https://doi.org/10.5281/zenodo.3) | 66158 | 12.4 MB | More rows. |") in readme
    assert "(none yet)" in metadata.registry_readme(
        {"lmfdb_version": "2.0", "tables": {}}, {}, "")
    assert "includes 1 of the 2 tables" in readme


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
    monkeypatch.setattr(state, "history_lock", lambda db: contextlib.nullcontext())
    monkeypatch.setattr(state, "latest_deploy_id", lambda db: len(calls))
    cfg = SimpleNamespace(editor=None)
    b, c, d, e, f, g, x = (ch * 40 for ch in "bcdefgx")
    # B's workflow failed, C was pushed and recorded, then B is rerun
    assert watcher.record_deploy(None, b, major=2, config=cfg, observe=lambda: c) is None
    event = watcher.record_deploy(None, c, major=2, config=cfg, observe=lambda: c)
    assert (event["kind"], event["seq"]) == ("code", 2)
    assert watcher.record_deploy(None, c, major=2, config=cfg, observe=lambda: c) is None
    # a concurrent recorder that checked before C was recorded rechecks
    # once it holds the history lock
    assert watcher._record(None, c, 2, "proddb", dry_run=False) is None
    assert len(calls) == 1

    # E was the head when observed, but F was pushed and recorded while E was
    # being checked: looking again, E is no longer the head
    heads = [e, f]

    def observe_e():
        if heads[0] == e:
            watcher.record_deploy(None, f, major=2, config=cfg)
        return heads.pop(0)

    assert watcher.record_deploy(None, e, major=2, config=cfg, observe=observe_e) is None
    # conversely, a late fallback records an older X while the Action for the
    # head G checks: looking again, G is still the head, so it is recorded
    late = [x]

    def observe_g():
        if late:
            watcher.record_deploy(None, late.pop(), major=2, config=cfg)
        return g

    assert watcher.record_deploy(None, g, major=2, config=cfg,
                                 observe=observe_g)["git_hash"] == g
    assert [r[0]["git_hash"] for r in calls] == [c, f, x, g]

    # and if other deploys keep landing, it fails rather than succeed silently
    def busy():
        watcher.record_deploy(None, "%040d" % len(calls), major=2, config=cfg)
        return d

    with pytest.raises(RuntimeError, match="re-run"):
        watcher.record_deploy(None, d, major=2, config=cfg, observe=busy, tries=2)
    # a major bump writes its two rows in a single statement
    watcher.record_deploy(None, d, major=3, config=cfg, observe=lambda: d)
    assert [(r["kind"], r["major"], r["seq"]) for r in calls[-1]] == [
        ("major", 3, 3), ("code", 3, 0)]


def test_backfill_redumps_after_a_newer_push(offline_backup, tmp_path, monkeypatch):
    from datetime import timedelta
    backup, published, attempts = offline_backup
    published.clear()
    monkeypatch.setattr(backup, "load_tables_yaml", lambda path=None: {
        "zzz_a": {"backup": "yes"}})
    dumps = []

    class DB:
        tablenames = ["zzz_a"]

        def table_sizes(self):
            return {}

        def copy_to(self, tables, folder):
            make_dump(folder, tables[0])
            dumps.append(folder)

    monkeypatch.setattr(backup, "backup_folder",
                        lambda db, folder, tables, **kwds: {"paused": tables})
    cfg = prod_config(tmp_path, enabled=True)
    backup.backfill(DB(), dry_run=False, config=cfg)
    taken = backup._dump_time(dumps[0])
    # the backfill's own paused upload: its dump is reused
    attempts["zzz_a"] = {"status": "awaiting_quota", "source_time": taken}
    backup.backfill(DB(), dry_run=False, config=cfg)
    assert len(dumps) == 1
    # a push reloaded zzz_a since, and its upload paused too: dump again
    attempts["zzz_a"] = {"status": "awaiting_quota",
                         "source_time": taken + timedelta(seconds=1)}
    backup.backfill(DB(), dry_run=False, config=cfg)
    assert len(dumps) == 2


def test_backfill_reports_skipped_tables(offline_backup, tmp_path, monkeypatch, capsys):
    backup, published, attempts = offline_backup
    published.clear()
    monkeypatch.setattr(backup, "load_tables_yaml", lambda path=None: {
        "zzz_a": {"backup": "yes"}, "zzz_b": {"backup": "hold"},
        "zzz_c": {"backup": "no"}, "zzz_gone": {"backup": "yes"}})

    class DB:
        tablenames = ["zzz_a", "zzz_b", "zzz_c", "zzz_new"]

        def table_sizes(self):
            return {}

    assert backup.backfill(DB(), config=prod_config(tmp_path)) == ["zzz_a"]
    out = capsys.readouterr().out
    assert "On hold in tables.yaml (skipped): zzz_b\n" in out
    assert "not in the database (skipped): zzz_gone\n" in out


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
    cfg = prod_config(tmp_path, enabled=True)
    assert backup.backfill(DB(), config=cfg) == names
    assert backup.backfill(DB(), config=cfg, first=["zzz_c"]) == ["zzz_c", "zzz_a", "zzz_b"]
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
    # a run interrupted after verifying zzz_a, before deleting its dump
    (root / "zzz_a").mkdir()
    attempts["zzz_a"] = {"status": "verified"}
    backup.backfill(DB(), dry_run=False, config=cfg)
    assert not list(root.iterdir())


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
    params = conninfo_to_dict(dsn)
    # psycodict reconnects with the configured options, not the connect
    # arguments, so the configuration must name the scratch database too
    defaults = {"postgresql_" + k: v for k, v in params.items()
                if k in ("host", "port", "user", "password", "dbname")}
    defaults["config_file"] = str(tmp_path / "psycodict.ini")
    config = Configuration(readargs=False, defaults=defaults)
    db = PostgresDatabase(config=config, create=True, **params)
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


def test_current_version_string(scratch_db):
    from lmfdb.zenodo import state
    db = scratch_db
    assert state.current_version_string(db) is None
    state.ensure_tables(db)
    assert state.current_version_string(db) is None
    state.insert_major(db, 2)
    assert state.current_version_string(db) == "2.0-0"


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
    depositions refuse edits; setting ``lose_publish_response`` to a word of
    a record's title makes its next publication succeed but its response
    fail; ``fail_upload`` names a file whose next upload fails.  Records are
    verified by the real client's checks.  The community listing leaves out
    the records in ``unlisted`` until they are re-published (unless also
    ``stuck``), and those in ``outside``, which are not members.
    """
    verify_record = ZenodoClient.verify_record

    def __init__(self):
        self.deps, self.next_id, self.blocked = {}, 100, set()
        self.lose_publish_response = self.fail_upload = self.on_publish = None
        self.uploads, self.quota_raises, self.refuse_quota = [], [], False
        self.ops = []  # ("delete" | "upload", filename), in order
        self.lose_new_version_response = False
        self.unlisted, self.stuck, self.outside = set(), set(), set()
        self.republished = []

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
        from lmfdb.zenodo.client import NotFound
        if int(dep_id) not in self.deps:
            raise NotFound("get deposition %s: 404" % dep_id)
        return self.deps[int(dep_id)]

    def get_record(self, recid):
        files = self.deps.get(int(recid), {}).get("files", {})
        return {"files": [{"key": name, "checksum": "md5:" + md5}
                          for name, md5 in files.items()],
                "metadata": {"communities": [] if int(recid) in self.outside
                             else [{"id": "lmfdb"}]}}

    def in_community(self, community, recid):
        return int(recid) not in self.unlisted | self.outside

    def republish(self, recid):
        self.republished.append(int(recid))
        if int(recid) not in self.stuck:
            self.unlisted.discard(int(recid))

    def new_version(self, recid):
        # like Zenodo's RDM API: an open new-version draft is returned again
        prev = self.deps[int(recid)]
        open_ = [d for d in self.deps.values()
                 if d["concept"] == prev["concept"] and not d["submitted"]]
        dep = open_[0] if open_ else self._new(prev["files"], prev["concept"])
        if self.lose_new_version_response:
            self.lose_new_version_response = False
            raise ConnectionError("connection reset after creating the draft")
        return dep

    def raise_quota(self, dep_id, gb):
        from lmfdb.zenodo.client import ZenodoError
        if self.refuse_quota:
            raise ZenodoError("raise quota of %s: 403 permission denied" % dep_id)
        self.quota_raises.append((int(dep_id), gb))

    def delete_draft(self, dep_id):
        from lmfdb.zenodo.client import NotFound
        if self.deps.pop(int(dep_id), None) is None:
            raise NotFound("discard draft %s: 404" % dep_id)

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
        self.ops.append(("delete", link[1]))

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
        if name == self.fail_upload:
            self.fail_upload = None
            raise ConnectionError("connection reset during upload")
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        dep["files"][name] = md5
        self.uploads.append(name)
        self.ops.append(("upload", name))
        return {"checksum": "md5:" + md5}

    def publish(self, dep_id):
        dep = self.deps[int(dep_id)]
        if self.on_publish:
            self.on_publish(dep)
        dep.update(submitted=True, state="done", doi="10.5072/zenodo.%s" % dep["id"],
                   conceptrecid=dep["concept"],
                   conceptdoi="10.5072/zenodo.%s" % dep["concept"])
        lose = self.lose_publish_response
        if lose and lose in dep["metadata"]["title"]:
            self.lose_publish_response = None
            raise ConnectionError("connection reset after publishing")
        return {k: dep[k] for k in ["id", "doi", "conceptrecid", "conceptdoi"]}


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


def test_check_listings(tmp_path, monkeypatch):
    pytest.importorskip("psycodict")
    from lmfdb.zenodo import backup
    sleeps = []
    monkeypatch.setattr(backup.time, "sleep", sleeps.append)
    fake = FakeZenodo()
    cfg = ZenodoConfig(path=str(tmp_path / "missing.ini"))
    rows = {name: {"recid": str(i), "owner": "roe"}
            for i, name in [(1, "zzz_a"), (2, "zzz_b"), (3, "zzz_c"), (4, "zzz_d")]}
    fake.unlisted, fake.stuck, fake.outside = {2, 4}, {4}, {3}

    def check(repair, wait=0):
        return backup._check_listings(cfg, rows, lambda owner: fake, repair, wait)
    problems = check(repair=False)
    assert sorted(problems) == ["zzz_b", "zzz_c", "zzz_d"] and not fake.republished
    assert "awaiting a curator" in problems["zzz_c"]
    monkeypatch.setattr(backup, "LISTING_WAIT", 0)
    problems = check(repair=True)
    assert fake.republished == [2, 4]
    assert sorted(problems) == ["zzz_c", "zzz_d"]
    assert "after re-publishing" in problems["zzz_d"]
    # a record indexed a little late needs no repair
    rows = {"zzz_e": {"recid": "5", "owner": "roe"}}
    lookups = []

    def late(community, recid):
        lookups.append(recid)
        return len(lookups) > 2
    fake.in_community = late
    assert check(repair=True, wait=1000) == {}
    assert len(lookups) == 3 and len(sleeps) == 2 and fake.republished == [2, 4]


def test_push_waits_for_paused_upload(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    for t in ["zzz_a", "zzz_b"]:
        make_dump(tmp_path / "push1", t)
        make_dump(tmp_path / "push2", t, nrows=30)
    records = tmp_path / "staging" / "records"
    plan = backup.backup_folder(db, tmp_path / "push1", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.1" and not list(records.iterdir())
    # both tables change; zzz_b needs more quota than its owner has
    fake.blocked.add("zzz_b")
    plan = backup.backup_folder(db, tmp_path / "push2", dry_run=False, live=True,
                                config=cfg, description="More rows.", bump="minor")
    assert plan["paused"] == ["zzz_b"] and plan["version"] is None
    assert [p.name for p in records.iterdir()] == ["zzz_b"]
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
    assert not list(records.iterdir())


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
    fake.lose_publish_response = "zzz_a"
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                             config=cfg)
    row = state.latest_attempt(db, "zzz_a")
    assert row["status"] == "uploading" and row["draft_id"]
    draft = row["draft_id"]
    package = tmp_path / "staging" / "records" / "zzz_a"
    assert package.exists()
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.1" and not package.exists()
    row = state.latest_attempt(db, "zzz_a")
    assert (row["status"], row["recid"]) == ("verified", draft)


def test_newer_dump_after_lost_publish_response(scratch_db, tmp_path, monkeypatch):
    from psycodict import SQL
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "v1", "zzz_a")
    make_dump(tmp_path / "v2", "zzz_a", nrows=30)
    fake.lose_publish_response = "zzz_a"
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "v1", dry_run=False, live=True,
                             config=cfg)
    # v1 was published without our hearing back; then a corrected v2 arrives,
    # which becomes the next version rather than being credited to v1's record
    plan = backup.backup_folder(db, tmp_path / "v2", dry_run=False, live=True,
                                config=cfg, description="Corrected.", bump="minor")
    assert plan["version"] == "2.1"
    rows = state._backup_rows(db, SQL(" WHERE tablename = 'zzz_a' ORDER BY id"), None)
    assert [(r["status"], r["version"]) for r in rows] == [
        ("verified", "1.0"), ("verified", "1.1")]
    assert rows[0]["source_md5s"] == packaging.source_md5s(tmp_path / "v1", "zzz_a")
    assert rows[1]["recid"] != rows[0]["recid"]
    assert state.resolve_version(db, 2, 1)["tables"]["zzz_a"]["version"] == "1.1"
    assert backup.backup_folder(db, tmp_path / "v2", config=cfg)["skip_unchanged"] == ["zzz_a"]


def test_discarded_draft_is_replaced(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")
    fake.blocked.add("zzz_a")
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    draft = int(state.latest_attempt(db, "zzz_a")["draft_id"])
    # the owner discards the paused draft on Zenodo instead of raising the quota
    del fake.deps[draft]
    fake.blocked.clear()
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    row = state.latest_attempt(db, "zzz_a")
    assert plan["version"] == "2.1" and row["status"] == "verified"
    assert int(row["recid"]) != draft


@pytest.mark.parametrize("record", ["knowls", "registry"])
def test_lost_special_record_response_is_recovered(scratch_db, tmp_path,
                                                   monkeypatch, record):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")
    # the registry's first version (2.0), published before any other record
    backup._ensure_registry(db, cfg, True, tmp_path / "staging" / "records")
    fake.lose_publish_response = record
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                             config=cfg)
    # the registry names its data version, so it is published only after the
    # version is recorded
    assert (state.latest_data_row(db) is not None) == (record == "registry")
    backup.finalize(db, cfg=cfg, live=True)
    # each record was published exactly once, and no draft was left behind:
    # registry 2.0, zzz_a, the knowls and registry 2.1
    assert len(fake.deps) == 4
    assert all(dep["submitted"] for dep in fake.deps.values())
    assert set(state.resolve_version(db, 2, 1)["tables"]) == {
        "zzz_a", backup.KNOWLS_NAME, backup.REGISTRY_NAME}


def test_data_version_follows_active_major(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push1", "zzz_a")
    plan = backup.backup_folder(db, tmp_path / "push1", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.1"
    # major 3 is deployed while this session's lmfdb.version still says 2
    state.insert_major(db, 3)
    make_dump(tmp_path / "push2", "zzz_a", nrows=30)
    make_dump(tmp_path / "push2", "zzz_b")
    insert = state.insert_version_rows

    def fail_once(db, rows):
        monkeypatch.setattr(state, "insert_version_rows", insert)
        raise RuntimeError("connection lost")

    monkeypatch.setattr(state, "insert_version_rows", fail_once)
    with pytest.raises(RuntimeError, match="connection lost"):
        backup.backup_folder(db, tmp_path / "push2", dry_run=False, live=True,
                             config=cfg, description="More rows.", bump="minor")
    # major 4 arrives before the push is finalized: the batch keeps its tables
    state.insert_major(db, 4)
    plan = backup.backup_folder(db, tmp_path / "push2", dry_run=False, live=True,
                                config=cfg)
    assert plan["skip_unchanged"] == ["zzz_a", "zzz_b"] and plan["version"] == "4.1"
    tables = state.resolve_version(db, 4, 1)["tables"]
    assert (tables["zzz_a"]["version"], tables["zzz_b"]["version"]) == ("1.1", "1.0")
    assert [(r["major"], r["seq"]) for r in state.history(db)
            if r["kind"] == "data"] == [(4, 1), (2, 1)]
    # published while 3.1 was expected, the record names no data version
    description = fake.deps[int(tables["zzz_a"]["recid"])]["metadata"]["description"]
    assert "3.1" not in description and "lmfdb.org/version" in description


def test_finalize_lists_records_missing_from_history(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "a", "zzz_a")
    make_dump(tmp_path / "b", "zzz_b")
    assert backup.backup_folder(db, tmp_path / "a", dry_run=False, live=True,
                                config=cfg)["version"] == "2.1"
    backup.backup_folder(db, tmp_path / "b", dry_run=False, live=True, config=cfg,
                         finalize_version=False)
    # as left by a finalize that also picked 2.1 and lost the race to record it
    state.update_attempt(db, state.latest_published(db, "zzz_b")["id"],
                         lmfdb_version="2.1")
    assert backup.finalize(db, cfg=cfg, live=True) == "2.2"
    assert "zzz_b" in state.resolve_version(db, 2, 2)["tables"]


def test_archive_runs_are_serialized(scratch_db, tmp_path, monkeypatch):
    import threading
    import psycopg
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(state, "LOCK_POLL", 0.05)
    make_dump(tmp_path / "push", "zzz_a")
    result = {}
    with psycopg.connect(os.environ["LMFDB_ZENODO_TEST_DB"], autocommit=True) as other:
        other.execute("SELECT pg_advisory_lock(hashtext('version_history'))")
        run = threading.Thread(target=lambda: result.update(plan=backup.backup_folder(
            db, tmp_path / "push", dry_run=False, live=True, config=cfg)))
        run.start()
        run.join(1)
        assert run.is_alive() and not fake.deps  # waiting, nothing uploaded
        other.execute("SELECT pg_advisory_unlock(hashtext('version_history'))")
        run.join(60)
    assert result["plan"]["version"] == "2.1"


def test_interrupted_upload_counts_sent_bytes(scratch_db, tmp_path, monkeypatch):
    from datetime import datetime
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(packaging, "zstd_available", lambda: False)
    make_dump(tmp_path / "push", "zzz_a")
    fake.fail_upload = "zzz_a_stats.txt.gz"
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                             config=cfg)
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    row = state.latest_published(db, "zzz_a")
    # a first version: this attempt sent every file, before or after the failure
    assert sum(f["size"] for f in row["uploaded_files"].values()
               if not f.get("reused")) == row["total_size"]
    assert state.uploaded_bytes_since(db, datetime(2026, 1, 1)) >= row["total_size"]


def test_resumed_upload_keeps_its_package(scratch_db, tmp_path, monkeypatch):
    from datetime import datetime
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(packaging, "zstd_available", lambda: False)
    manifests = []
    real = packaging.package_table
    monkeypatch.setattr(packaging, "package_table", lambda *args, **kwds:
                        manifests.append(real(*args, **kwds)) or manifests[-1])
    make_dump(tmp_path / "push", "zzz_a")
    fake.fail_upload = "zzz_a_stats.txt.gz"
    reloaded = datetime(2026, 1, 2, 3, 4, 5)
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                             config=cfg, source_time=reloaded)

    compress = packaging.compress_file

    def compress_knowls(src, *args, **kwds):
        assert not src.name.startswith("zzz_a"), "compressed again"
        return compress(src, *args, **kwds)
    monkeypatch.setattr(packaging, "compress_file", compress_knowls)
    fake.uploads.clear()
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    assert [f for f in fake.uploads
            if f.startswith("zzz_a") and f.endswith(".gz")] == ["zzz_a_stats.txt.gz"]
    assert manifests[-1]["source_time"] == "2026-01-02T03:04:05Z"
    assert state.latest_published(db, "zzz_a")["status"] == "verified"


def test_gzip_artifacts_of_unchanged_files_are_reused(scratch_db, tmp_path,
                                                      monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(packaging, "zstd_available", lambda: False)
    make_dump(tmp_path / "push", "zzz_a")
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    (tmp_path / "push" / "zzz_a_counts.txt").write_text("row0|recounted\n")
    fake.uploads.clear()
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                         config=cfg, description="Recounted.", bump="minor")
    assert "zzz_a_counts.txt.gz" in fake.uploads
    assert "zzz_a.txt.gz" not in fake.uploads
    assert state.latest_published(db, "zzz_a")["uploaded_files"]["zzz_a.txt.gz"]["reused"]


def test_audit_compares_with_snapshot_time(scratch_db, tmp_path, monkeypatch):
    from datetime import datetime
    from psycodict import SQL
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    db._execute(SQL("CREATE TABLE userdb.dbrecord "
                    "(tablename text, operation text, time timestamp)"))
    db.tablenames = ["zzz_a", "zzz_b"]
    # dumped at 12:00, changed on production at 12:05, upload finished at 12:10
    for name in db.tablenames:
        aid = state.start_attempt(db, name, "roe", "1.0", {},
                                  source_time=datetime(2026, 11, 16, 12, 0))
        state.update_attempt(db, aid, status="verified",
                             finished=datetime(2026, 11, 16, 12, 10))
    # a dropped column changes the archived dump; copying the table does not
    db._execute(SQL("INSERT INTO userdb.dbrecord VALUES "
                    "('zzz_a', 'drop_column', '2026-11-16 12:05'), "
                    "('zzz_b', 'create_table_like', '2026-11-16 12:05')"))
    assert backup.audit(db, config=cfg)["changed_since_archive"] == ["zzz_a"]


def test_major_bump_during_finalize(scratch_db, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from lmfdb.zenodo import watcher
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")

    def deploy(dep):  # major 3 is deployed while the knowls record goes up
        if "knowls" in dep["metadata"]["title"]:
            watcher.record_deploy(db, "c" * 40, major=3, observe=lambda: "c" * 40,
                                  config=SimpleNamespace(editor=None))

    fake.on_publish = deploy
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "3.1" and state.current_version_string(db) == "3.1-0"
    assert "zzz_a" in state.resolve_version(db, 3, 1)["tables"]


def test_reconnect_loses_the_archive_lock(scratch_db):
    from lmfdb.zenodo import state
    db = scratch_db
    state.ensure_tables(db)
    aid = state.start_attempt(db, "zzz_a", "roe", "1.0", {})
    assert db.config.options["postgresql"]["port"] == db.conn.info.port
    with state.lock(db):
        db.conn.close()  # the connection drops, and the lock with it
        # psycodict reconnects, but does not replay the write on the new session
        with pytest.raises(Exception):
            state.update_attempt(db, aid, error="written without the lock")
        with pytest.raises(state.LockLost):
            state.update_attempt(db, aid, error="written without the lock")
    assert state.get_attempt(db, aid)["error"] is None


def test_restored_data_retires_paused_upload(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "a", "zzz_a")
    make_dump(tmp_path / "b", "zzz_a", nrows=30)
    make_dump(tmp_path / "c", "zzz_b")
    backup.backup_folder(db, tmp_path / "a", dry_run=False, live=True, config=cfg)
    fake.blocked.add("zzz_a")
    backup.backup_folder(db, tmp_path / "b", dry_run=False, live=True, config=cfg,
                         description="More rows.", bump="minor")
    draft = int(state.latest_attempt(db, "zzz_a")["draft_id"])
    # production is restored to the archived data before the quota is raised
    plan = backup.backup_folder(db, tmp_path / "a", dry_run=False, live=True,
                                config=cfg)
    assert plan["skip_unchanged"] == ["zzz_a"] and draft not in fake.deps
    assert state.latest_attempt(db, "zzz_a")["status"] == "superseded"
    assert not (tmp_path / "staging" / "records" / "zzz_a").exists()
    # so other pushes are not blocked
    plan = backup.backup_folder(db, tmp_path / "c", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.2"


def test_audit_reports_unverified_records(scratch_db, tmp_path, monkeypatch):
    from psycodict import SQL
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    db._execute(SQL("CREATE TABLE userdb.dbrecord "
                    "(tablename text, operation text, time timestamp)"))
    db.tablenames = ["zzz_a"]
    aid = state.start_attempt(db, "zzz_a", "roe", "1.0", {})
    state.update_attempt(db, aid, status="published", recid="1",
                         error="zzz_a.txt.zst: checksum mismatch")
    report = backup.audit(db, config=cfg)
    assert [r["tablename"] for r in report["unverified"]] == ["zzz_a"]


def test_quota_is_raised_for_large_records(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(backup, "DEFAULT_QUOTA", 1000)  # every table is "large"
    make_dump(tmp_path / "push", "zzz_a")
    # the owner's allowance is used up
    fake.refuse_quota = True
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    row = state.latest_attempt(db, "zzz_a")
    assert plan["paused"] == ["zzz_a"] and row["status"] == "awaiting_quota"
    assert "quota increase to 1 GB refused" in row["error"]
    assert not [name for name in fake.uploads if name.startswith("zzz_a")]
    # once it is freed, re-running raises the quota and completes the push
    fake.refuse_quota = False
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    recid = int(state.latest_published(db, "zzz_a")["recid"])
    assert plan["version"] == "2.1" and (recid, 1) in fake.quota_raises


def test_push_republishes_records_missing_from_the_listing(scratch_db, tmp_path,
                                                        monkeypatch):
    from psycodict import SQL
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(backup, "LISTING_WAIT", 0)
    for t in ["zzz_a", "zzz_b"]:
        make_dump(tmp_path / "push", t)
    fake.on_publish = lambda dep: (fake.unlisted.add(dep["id"])
                                   if "zzz_b" in dep["metadata"]["title"] else None)
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg)
    recid = int(state.latest_published(db, "zzz_b")["recid"])
    assert plan["version"] == "2.1" and fake.republished == [recid]
    assert not fake.unlisted
    # the audit only reports; reindex repairs
    db._execute(SQL("CREATE TABLE userdb.dbrecord "
                    "(tablename text, operation text, time timestamp)"))
    db.tablenames = ["zzz_a", "zzz_b"]
    fake.unlisted.add(recid)
    assert backup.audit(db, config=cfg, live=True)["unlisted"] == ["zzz_b"]
    assert backup.audit(db, config=cfg)["unlisted"] == []
    assert fake.republished == [recid]
    assert backup.reindex(db, tables=["zzz_b"], live=True, config=cfg) == {}
    assert fake.republished == [recid, recid] and not fake.unlisted


def test_update_prod_lock_is_reentrant(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")
    # as in update_prod: reload and archive under one hold of the lock
    with backup.archive_lock(db, cfg):
        plan = backup.backup_folder(db, tmp_path / "push", dry_run=False,
                                    live=True, config=cfg)
    assert plan["version"] == "2.1"


def test_lost_lock_stops_zenodo_calls(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")
    fake.blocked.add("zzz_a")
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    draft = int(state.latest_attempt(db, "zzz_a")["draft_id"])
    with state.lock(db):
        db.conn.close()  # the lock goes with the connection
        with pytest.raises(state.LockLost):
            backup._retire(db, cfg, True, "zzz_a", "production restored",
                           tmp_path / "staging" / "records")
    assert draft in fake.deps


def test_changed_files_are_removed_before_uploads(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(packaging, "zstd_available", lambda: False)
    monkeypatch.setattr(backup, "DEFAULT_QUOTA", 1000)  # every table is "large"
    make_dump(tmp_path / "v1", "zzz_a")
    make_dump(tmp_path / "v2", "zzz_a", nrows=30)
    backup.backup_folder(db, tmp_path / "v1", dry_run=False, live=True, config=cfg)
    raises = len(fake.quota_raises)
    fake.ops.clear()
    backup.backup_folder(db, tmp_path / "v2", dry_run=False, live=True, config=cfg,
                         description="More rows.", bump="minor")
    table_ops = [op for op, name in fake.ops if name.startswith("zzz_a")]
    deleted = {name for op, name in fake.ops if op == "delete"}
    # the new version's draft never holds both contents of a changed file
    assert "zzz_a.txt.gz" in deleted
    assert table_ops == sorted(table_ops)  # every "delete" before any "upload"
    # and the quota already set for the record is not set again
    assert len(fake.quota_raises) == raises


def test_quota_requested_again_for_a_new_record(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    monkeypatch.setattr(packaging, "zstd_available", lambda: False)
    monkeypatch.setattr(backup, "DEFAULT_QUOTA", 1000)  # every table is "large"
    make_dump(tmp_path / "push", "zzz_a")
    fake.fail_upload = "zzz_a_stats.txt.gz"
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                             config=cfg)
    first = int(state.latest_attempt(db, "zzz_a")["draft_id"])
    del fake.deps[first]  # the owner discards the unpublished draft
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    second = int(state.latest_published(db, "zzz_a")["recid"])
    assert [d for d, gb in fake.quota_raises if d in (first, second)] == [first, second]


def test_lost_new_version_response(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "v1", "zzz_a")
    make_dump(tmp_path / "v2", "zzz_a", nrows=30)
    backup.backup_folder(db, tmp_path / "v1", dry_run=False, live=True, config=cfg)
    fake.lose_new_version_response = True
    with pytest.raises(ConnectionError):
        backup.backup_folder(db, tmp_path / "v2", dry_run=False, live=True,
                             config=cfg, description="More rows.", bump="minor")
    plan = backup.backup_folder(db, tmp_path / "v2", dry_run=False, live=True,
                                config=cfg)
    assert plan["version"] == "2.2"
    # the draft made by the lost call became version 1.1; none is left over
    concept = fake.deps[int(state.latest_published(db, "zzz_a")["recid"])]["concept"]
    assert [d["submitted"] for d in fake.deps.values()
            if d["concept"] == concept] == [True, True]


def test_attempt_handover_is_atomic(scratch_db, monkeypatch):
    from psycodict import SQL
    from lmfdb.zenodo import backup, state
    db = scratch_db
    state.ensure_tables(db)
    old = state.start_attempt(db, "zzz_a", "roe", "1.0", {"a": "1"})
    state.update_attempt(db, old, status="awaiting_quota", draft_id="100")
    update = state.update_attempt

    def interrupted(db, aid, **fields):
        if fields.get("status") == "superseded":
            raise RuntimeError("interrupted")
        update(db, aid, **fields)

    monkeypatch.setattr(state, "update_attempt", interrupted)
    with pytest.raises(RuntimeError):
        backup._resume_or_start(db, "zzz_a", {
            "owner": "roe", "version": "1.0", "bump": None, "notes": None,
            "source_md5s": {"a": "2"}, "source_time": None})
    rows = state._backup_rows(db, SQL(" ORDER BY id"), None)
    assert [(r["status"], r["draft_id"]) for r in rows] == [("awaiting_quota", "100")]


def test_provenance():
    from datetime import datetime
    pytest.importorskip("psycodict")
    from lmfdb.zenodo import backup
    info = backup._provenance(datetime(2026, 11, 17, 7, 22, 26, 635241))
    assert info["source_time"] == "2026-11-17T07:22:26Z"
    assert info["exporter"]["psycodict"]


def test_records_link_to_the_registry(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "v1", "zzz_a")
    make_dump(tmp_path / "v2", "zzz_a", nrows=30)
    backup.backup_folder(db, tmp_path / "v1", dry_run=False, live=True, config=cfg)
    registry = state.latest_published(db, backup.REGISTRY_NAME)
    table = state.latest_published(db, "zzz_a")
    reg_md = fake.deps[int(registry["recid"])]["metadata"]
    assert reg_md["version"] == "2.1"
    assert {"identifier": table["doi"], "relation": "hasPart"} in reg_md["related_identifiers"]
    assert "README.md" in fake.deps[int(registry["recid"])]["files"]
    # the registry's first version, 2.0, was published before anything else,
    # so even the first versions of the table and the knowls point to it
    link = {"identifier": registry["concept_doi"], "relation": "isPartOf"}
    knowls = state.latest_published(db, backup.KNOWLS_NAME)
    for row in (table, knowls):
        assert link in fake.deps[int(row["recid"])]["metadata"]["related_identifiers"]
    assert table["nrows"] == 20 and state.resolve_version(db, 2, 1)["tables"]["zzz_a"]["rows"] == 20
    backup.backup_folder(db, tmp_path / "v2", dry_run=False, live=True, config=cfg,
                         description="More rows.", bump="minor")
    table_md = fake.deps[int(state.latest_published(db, "zzz_a")["recid"])]["metadata"]
    assert link in table_md["related_identifiers"]


def test_force_regenerates_every_record(scratch_db, tmp_path, monkeypatch):
    db = scratch_db
    backup, state, fake, cfg = push_setup(db, tmp_path, monkeypatch)
    make_dump(tmp_path / "push", "zzz_a")
    backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True, config=cfg)
    # the same data again, forced: new versions of the table and the knowls
    # (not new records), so their documentation is regenerated
    plan = backup.backup_folder(db, tmp_path / "push", dry_run=False, live=True,
                                config=cfg, force=True,
                                description="Regenerated documentation.", bump="minor")
    assert plan["version"] == "2.2"
    tables = state.resolve_version(db, 2, 2)["tables"]
    assert (tables["zzz_a"]["version"], tables[backup.KNOWLS_NAME]["version"]) == ("1.1", "1.1")
    assert len({dep["concept"] for dep in fake.deps.values()}) == 3


def test_state_tables_gain_new_columns(scratch_db, tmp_path):
    from psycodict import SQL
    from lmfdb.zenodo import backup, state
    db = scratch_db
    state.ensure_tables(db)
    aid = state.start_attempt(db, "zzz_a", "roe", "1.0", {})
    # as created by an earlier version of this code
    db._execute(SQL("ALTER TABLE userdb.zenodo_backups DROP COLUMN nrows"))
    backup._state_db(db, prod_config(tmp_path))
    state.update_attempt(db, aid, nrows=5)
    assert state.get_attempt(db, aid)["nrows"] == 5
    # and for the sandbox state, which is created on first use
    sandbox = ZenodoConfig(path=str(tmp_path / "missing.ini"))
    sdb = backup._state_db(db, sandbox)
    db._execute(SQL("ALTER TABLE userdb.zenodo_backups_sandbox DROP COLUMN quota_gb"))
    sdb = backup._state_db(db, sandbox)
    assert state.unfinished(sdb) == []
