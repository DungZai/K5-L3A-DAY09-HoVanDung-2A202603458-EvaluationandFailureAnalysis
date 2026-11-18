"""Keep the eval-set bytes stable across Windows builds and Linux Git checkouts."""
import hashlib
import json

import pytest

from lab9 import evalset

pytestmark = pytest.mark.student


def test_built_evalset_uses_lf_for_portable_sha(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "claims.jsonl"
    source.write_text(json.dumps({"claim_id": "C-001", "matrix_id": "T01",
                                  "expected": {"refund_vnd": 35000}}), encoding="utf-8")
    evalset.build(source)
    raw = evalset.ITEMS.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert evalset.sha12(evalset.ITEMS) == hashlib.sha256(raw).hexdigest()[:12]
