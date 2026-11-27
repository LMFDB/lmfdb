from types import SimpleNamespace

from sage.all import ZZ

from lmfdb.lmfdb_database import LMFDBDatabase, _cap_log_payload


def test_small_payload_unchanged():
    data = {"query": {"label": "11.a1"}, "changes": {"rank": ZZ(0)}}
    assert _cap_log_payload(data) is data


def test_large_payload_keeps_shape():
    record = {"label": "11.a1", "ainvs": list(range(500)), "conductor": 11}
    data = {"query": {"label": "11.a1"}, "data": record, "blob": "x" * 3000}
    capped = _cap_log_payload(data)
    assert capped["query"] == {"label": "11.a1"}
    assert capped["data"] == ["ainvs", "conductor", "label"]
    assert capped["blob"] == "<3002 bytes omitted>"
    assert capped["omitted_bytes"] > 5000


def test_payload_without_large_values_unchanged():
    data = {"k%s" % i: "x" * 190 for i in range(12)}
    assert _cap_log_payload(data) is data


def test_log_db_change_stores_capped_payload():
    calls = []
    fake_db = SimpleNamespace(login=lambda: "editor", _execute=lambda sql, values: calls.append(values))
    big = {"label": "11.a1", "ainvs": list(range(1000))}
    LMFDBDatabase._log_db_change(fake_db, "upsert", tablename="ec_curvedata", logid=1,
                                 query={"label": "11.a1"}, data=big)
    username, _, tablename, logid, operation, payload = calls[0]
    assert (username, tablename, logid, operation) == ("editor", "ec_curvedata", 1, "upsert")
    assert payload["data"] == ["ainvs", "label"]
    assert payload["query"] == {"label": "11.a1"}
