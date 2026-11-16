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

    # sample: 3 header lines + 10 rows of the search file
    sample = (outdir / (name + "_sample.txt")).read_text().splitlines()
    assert len(sample) == 13
    assert sample[0] == "id|label|dim"
    assert sample[3] == "0|lab.0|0"

    # README and MANIFEST written; manifest on disk matches return value
    assert (outdir / "README.md").read_text() == "# test readme\n"
    ondisk = json.loads((outdir / "MANIFEST.json").read_text())
    assert ondisk == manifest
    assert manifest["lmfdb_version"] == "2.1"
    assert manifest["record_version"] == "1.4"

    # upload order: README, sample, MANIFEST, then artifacts
    names = [p.name for p in packaging.upload_list(outdir)]
    assert names[:3] == ["README.md", name + "_sample.txt", "MANIFEST.json"]


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
    dst = dump / "sample.txt"
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


def test_change_info(offline_backup):
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
                                   None, None)
    backup.require_change_info(None, ["zzz_demo", "zzz_other"], "Fixed.", "minor")


def test_backup_plan(offline_backup, tmp_path):
    backup, published, attempts = offline_backup
    make_dump(tmp_path / "dump", "zzz_demo")
    make_dump(tmp_path / "dump", "zzz_other")
    cfg = ZenodoConfig(path=str(tmp_path / "missing.ini"))
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
