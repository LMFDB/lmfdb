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
    _class_to_int,
    _cremona_letter_code,
    format_version,
    parse_version,
)
from lmfdb.zenodo import packaging
from lmfdb.zenodo.client import NotLive, ZenodoClient
from lmfdb.zenodo.config import ZenodoConfig
from lmfdb.zenodo import metadata


######################################################################
# versioning                                                         #
######################################################################

def test_letter_code_known_values():
    for n, code in [(0, "a"), (1, "b"), (25, "z"), (26, "ba"), (27, "bb"),
                    (51, "bz"), (52, "ca"), (675, "zz"), (676, "baa")]:
        assert _cremona_letter_code(n) == code
        assert _class_to_int(code) == n


def test_letter_code_roundtrip():
    for n in range(2000):
        assert _class_to_int(_cremona_letter_code(n)) == n


def test_letter_code_matches_sage():
    try:
        import sage.all  # noqa: F401 -- initializes sage's import machinery
        from sage.databases.cremona import cremona_letter_code
    except Exception:
        pytest.skip("sage not available")
    for n in range(2000):
        assert _cremona_letter_code(n) == cremona_letter_code(n)
        assert _class_to_int(cremona_letter_code(n)) == n


def test_letter_code_errors():
    with pytest.raises(ValueError):
        _cremona_letter_code(-1)
    for bad in ["", "A", "b1", "2.3"]:
        with pytest.raises(ValueError):
            _class_to_int(bad)


def test_format_parse_version():
    assert format_version(2, 3, 26) == "2.3.ba"
    assert format_version(2, 0, 0) == "2.0.a"
    assert format_version(2, 3) == "2.3"
    assert parse_version("2.3.ba") == (2, 3, 26)
    assert parse_version("2.0.a") == (2, 0, 0)
    assert parse_version("2.3") == (2, 3, None)
    assert parse_version(" 10.20.zz ") == (10, 20, 675)
    for bad in ["", "2", "2.3.", "2.3.A", "1.2.1.4", "a.b.c", "2.-1.a"]:
        with pytest.raises(ValueError):
            parse_version(bad)


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
        readme="# test readme\n")
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
    desc = metadata.table_description_html(None, "zzz_demo", "2.1", nrows=17)
    assert "zzz_demo" in desc and "17" in desc
    readme = metadata.table_readme(None, "zzz_demo", "2.1")
    assert readme.startswith("# LMFDB table `zzz_demo`")
    assert "reload_all" in readme
    md = metadata.deposit_metadata(
        metadata.table_title("zzz_demo"), desc, "2.1",
        related_url="https://www.lmfdb.org/api/zzz_demo")["metadata"]
    assert md["title"] == "LMFDB table zzz_demo"
    assert md["license"] == "cc-by-sa-4.0"
    assert md["creators"] == [{"name": "The LMFDB Collaboration"}]
    assert md["version"] == "2.1"
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
# tables.yaml / eligibility (needs psycopg2 only for module import)  #
######################################################################

def test_tables_yaml():
    pytest.importorskip("psycopg2")
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
