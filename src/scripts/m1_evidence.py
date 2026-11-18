"""Replay M1 evidence without changing Lab 8 or requiring the unfinished M3 graders.

Run from src/: python -m scripts.m1_evidence
Only public synthetic canaries are present in these deliberately faulty traces.
"""
from __future__ import annotations

import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape


ANCHORS = [
    ("FM-01", "leaky_trace", "C-010"),
    ("FM-02", "ignore_denied", "C-007"),
    ("FM-03", "ticket_trust", "C-002"),
    ("FM-04", "sum_parts", "C-014"),
    ("FM-04-round", "round_down", "C-001"),
    ("FM-05", "pre_deducted", "C-014"),
    ("FM-06", "stale_clause", "C-006"),
    ("FM-07", "sibling_refund", "C-001"),
    ("FM-08", "misreport", "C-008"),
]


def replay(shape: str, claim: str, seed: int = 11) -> dict:
    trial = investigate(shape, claim, seed)["trial"]
    if not trial["events"] or trial["result"]["status"] == "error":
        raise RuntimeError(f"{shape} {claim}@{seed}: {trial['lab8_reason']}")
    return {
        "shape": shape, "claim_id": claim, "seed": seed,
        "run_id": trial["result"]["run_id"],
        "status": trial["result"]["status"],
        "proposal_amount": trial["result"]["proposal_amount"],
        "snapshot": trial["snapshot"], "unexpected_rows": trial["unexpected_rows"],
        "lab8_pass": trial["lab8_pass"], "lab8_reason": trial["lab8_reason"],
        "events": [{"step": n, **event} for n, event in enumerate(trial["events"], 1)],
    }


def main() -> None:
    utf8_stdio()
    evidence = {"generator": "python -m scripts.m1_evidence", "anchors": {}, "controls": {}}
    for fm, bug, claim in ANCHORS:
        shape = f"m1_{bug}"
        SHAPES[shape] = make_shape(shape, {"no_override", bug})
        row = replay(shape, claim)
        evidence["anchors"][fm] = row
        print(f"{fm}: {shape} {claim}@11 status={row['status']} "
              f"proposal={row['proposal_amount']} ledger={row['snapshot']['refund_vnd']} "
              f"unexpected={row['unexpected_rows']} lab8={row['lab8_reason']}")
    for n in range(1, 15):
        claim = f"C-{n:03d}"
        row = replay("fixed", claim)
        if not row["lab8_pass"]:
            raise AssertionError(f"fixed control failed: {claim}: {row['lab8_reason']}")
        evidence["controls"][claim] = row
    evidence["swarm_C-002@55"] = replay("swarm", "C-002", 55)
    # Replay every public item against each isolated bug. This supports item tags,
    # including negative controls where the same bug cannot affect the input.
    evidence["probes"] = {}
    for fm, bug, _ in ANCHORS:
        evidence["probes"][bug] = {
            f"C-{n:03d}": replay(f"m1_{bug}", f"C-{n:03d}")
            for n in range(1, 15)
        }
    out = Path("../docs/m1_trace_evidence.json")
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}; 9 bug replays, 14 passing fixed controls, 1 swarm replay")


if __name__ == "__main__":
    main()
