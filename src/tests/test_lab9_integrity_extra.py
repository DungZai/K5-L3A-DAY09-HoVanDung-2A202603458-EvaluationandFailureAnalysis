"""Additional M7 regressions: valid green runs, subtle report edits and ratchet."""
import copy
import itertools
import math

import pytest

from lab9 import gate, stats

pytestmark = pytest.mark.student


def green():
    rows = [{"item_id": f"E-{item}", "seed": seed, "pass_rate": True,
             "slices": ["money_movement"] if item == 0 else []}
            for item in range(3) for seed in range(1, 6)]
    report = {"manifest": {"eval_set_sha": "unchanged", "items": 3, "seeds": list(range(1, 6))},
              "rows": rows, "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}
    spec = {"eval_set_version": "v2", "metrics": [
        {"id": "pass_rate", "kind": "capability", "blocking": True,
         "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.8,
                    "blocking": True, "no_significant_drop": True}]}
    return report, spec


@pytest.mark.parametrize("edit", ["duplicate", "grader_failure", "none", "aggregate", "seed", "slice", "inf", "nan_row"])
def test_advanced_integrity_rejects_subtle_edits(edit):
    base, spec = green()
    pr = copy.deepcopy(base)
    if edit == "duplicate":
        pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    elif edit == "grader_failure":
        pr["evaluator_failures"] = ["a grader crashed even though all remaining rows are green"]
    elif edit == "none":
        pr["rows"][0]["pass_rate"] = None
    elif edit == "aggregate":
        pr["rows"][0]["pass_rate"] = False
    elif edit == "seed":
        for row in pr["rows"]:
            row["seed"] += 100
        pr["manifest"]["seeds"] = [s + 100 for s in pr["manifest"]["seeds"]]
    elif edit == "slice":
        for row in pr["rows"]:
            row["slices"] = []
    elif edit == "inf":
        pr["metrics"]["pass_rate"] = float("inf")
    elif edit == "nan_row":
        pr["rows"][0]["pass_rate"] = float("nan")
    assert gate.integrity_check(pr, base, spec)
    assert gate.check(pr, base, spec)[0] == ["integrity"]


@pytest.mark.parametrize("edit", ["metric", "slice", "blocking", "drop_ci", "slice_floor", "max"])
def test_advanced_ratchet_rejects_weaker_spec(edit):
    base, original = green()
    spec = copy.deepcopy(original)
    if edit == "metric":
        spec["metrics"] = []
    elif edit == "slice":
        spec["slices"] = []
    elif edit == "blocking":
        spec["metrics"][0]["blocking"] = False
    elif edit == "drop_ci":
        spec["metrics"][0]["threshold"].pop("no_significant_drop")
    elif edit == "slice_floor":
        spec["slices"][0]["min"] = 0.7
    elif edit == "max":
        original["metrics"][0]["threshold"]["max_increase"] = 0.1
        spec["metrics"][0]["threshold"]["max_increase"] = 0.2
    assert gate.integrity_check(base, base, spec, original)


def test_advanced_self_comparison_and_stricter_floor_are_allowed():
    base, spec = green()
    assert gate.integrity_check(base, base, spec, spec) == []
    assert gate.check(base, base, spec, spec)[0] == []
    tighter = copy.deepcopy(spec)
    tighter["metrics"][0]["threshold"]["min"] = 0.9
    assert gate.integrity_check(base, base, tighter, spec) == []


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
                                  (5, 2, 0), (5, 2, 6), (5.0, 2, 1), (5, True, 1)])
def test_advanced_both_pass_estimators_validate_args(args):
    for estimate in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            estimate(*args)


def test_advanced_pass_estimators_match_exhaustive_subsets():
    for n in range(1, 8):
        for c in range(n + 1):
            for k in range(1, n + 1):
                subsets = list(itertools.combinations([True] * c + [False] * (n - c), k))
                at_least_one = sum(any(s) for s in subsets) / len(subsets)
                all_pass = sum(all(s) for s in subsets) / len(subsets)
                assert math.isclose(stats.pass_at_k(n, c, k), at_least_one, abs_tol=1e-12)
                assert math.isclose(stats.pass_hat_k(n, c, k), all_pass, abs_tol=1e-12)
