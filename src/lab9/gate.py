"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    required_metrics = [m["id"] for m in spec["metrics"]]
    if len(set(required_metrics)) != len(required_metrics):
        problems.append("duplicate metric IDs in spec")

    def inspect(report: dict, name: str) -> dict:
        if not isinstance(report, dict):
            problems.append(f"{name}: report must be an object")
            return {}
        manifest, rows, metrics = report.get("manifest"), report.get("rows"), report.get("metrics")
        if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
            problems.append(f"{name}: malformed manifest, rows or metrics")
            return {}
        if report.get("evaluator_failures") != []:
            problems.append(f"{name}: evaluator_failures must be an empty list")
        if not isinstance(manifest.get("eval_set_sha"), str) or not manifest["eval_set_sha"]:
            problems.append(f"{name}: missing eval_set_sha")
        for mid, value in metrics.items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name}: metric {mid} is not finite")
        for mid in required_metrics:
            if mid not in metrics:
                problems.append(f"{name}: missing aggregate {mid}")
        items, seeds = manifest.get("items"), manifest.get("seeds")
        if (not isinstance(items, int) or isinstance(items, bool) or items < 1
                or not isinstance(seeds, list) or not seeds
                or any(not isinstance(s, int) or isinstance(s, bool) for s in seeds)
                or len(set(seeds)) != len(seeds)):
            problems.append(f"{name}: invalid item count or seeds")
            return {}
        if len(rows) != items * len(seeds):
            problems.append(f"{name}: row count != items x seeds")
        pairs, item_slices, item_seeds = {}, {}, {}
        row_metric_ids = [mid for mid in required_metrics if mid in GRADERS]
        valid_rows = True
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get("item_id"), str)
                    or not isinstance(row.get("seed"), int) or isinstance(row.get("seed"), bool)):
                problems.append(f"{name}: invalid row identity")
                valid_rows = False
                continue
            pair = row["item_id"], row["seed"]
            if pair in pairs:
                problems.append(f"{name}: duplicate item/seed {pair}")
            pairs[pair] = row
            if pair[1] not in seeds:
                problems.append(f"{name}: unlisted seed {pair}")
            item_seeds.setdefault(pair[0], set()).add(pair[1])
            tags = row.get("slices", [])
            if (not isinstance(tags, list) or any(not isinstance(t, str) for t in tags)
                    or len(set(tags)) != len(tags)):
                problems.append(f"{name}: invalid slices for {pair}")
            else:
                tagset = frozenset(tags)
                if pair[0] in item_slices and item_slices[pair[0]] != tagset:
                    problems.append(f"{name}: inconsistent slices across seeds for {pair[0]}")
                item_slices[pair[0]] = tagset
            for mid in row_metric_ids:
                if not isinstance(row.get(mid), bool):
                    problems.append(f"{name}: missing/non-boolean {mid} for {pair}")
                    valid_rows = False
            if "cost_per_success" in required_metrics:
                cost = row.get("cost")
                if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
                    problems.append(f"{name}: invalid cost for {pair}")
                    valid_rows = False
        if len(item_seeds) != items or any(have != set(seeds) for have in item_seeds.values()):
            problems.append(f"{name}: incomplete item x seed coverage")
        # Do not trust a green summary pasted over failing rows. Recompute all
        # declared aggregates that the harness knows how to derive from rows.
        if valid_rows and rows:
            k_values = set(spec.get("pass_k", []))
            for mid in required_metrics:
                if mid.startswith(("pass_at_", "pass_hat_")):
                    try:
                        k_values.add(int(mid.rsplit("_", 1)[1]))
                    except ValueError:
                        problems.append(f"{name}: invalid pass-k metric {mid}")
            calculated = aggregate([{**row, "cost": row.get("cost", 0)} for row in rows],
                                   row_metric_ids, k_values=sorted(k_values))
            for mid in required_metrics:
                actual, want = metrics.get(mid), calculated.get(mid)
                if mid not in calculated:
                    continue
                if (want is None or not isinstance(actual, (int, float))
                        or not math.isfinite(actual) or abs(actual - want) > 1e-8):
                    problems.append(f"{name}: aggregate {mid} disagrees with rows")
        return pairs

    pr_pairs, base_pairs = inspect(pr, "PR"), inspect(base, "baseline")
    if set(pr_pairs) != set(base_pairs):
        problems.append("PR item/seed set differs from baseline")
    for pair in pr_pairs.keys() & base_pairs.keys():
        left, right = pr_pairs[pair].get("slices", []), base_pairs[pair].get("slices", [])
        if (isinstance(left, list) and isinstance(right, list)
                and all(isinstance(t, str) for t in [*left, *right]) and set(left) != set(right)):
            problems.append(f"slice tags differ from baseline for {pair}")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def ratchet(old_entries, new_entries, key, prefix):
            old = {m[key]: m for m in old_entries}
            new = {m[key]: m for m in new_entries}
            if len(new) != len(new_entries):
                problems.append(f"ratchet: duplicate {prefix} identifiers")
            for mid, before in old.items():
                after = new.get(mid)
                if after is None:
                    problems.append(f"ratchet: removed {prefix} {mid}")
                    continue
                if before.get("blocking") and not after.get("blocking"):
                    problems.append(f"ratchet: disabled blocking {prefix} {mid}")
                for field in ("metric", "kind", "level", "grader"):
                    if field in before and after.get(field) != before[field]:
                        problems.append(f"ratchet: changed {field} of {prefix} {mid}")
                old_th = before.get("threshold", {}) if key == "id" else before
                new_th = after.get("threshold", {}) if key == "id" else after
                for field in ("min", "max", "max_increase"):
                    if field in old_th:
                        value = new_th.get(field)
                        if (not isinstance(value, (int, float)) or not math.isfinite(value)
                                or (value < old_th[field] if field == "min" else value > old_th[field])):
                            problems.append(f"ratchet: loosened {field} for {prefix} {mid}")
                if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                    problems.append(f"ratchet: removed no_significant_drop for {prefix} {mid}")
        ratchet(base_spec.get("metrics", []), spec.get("metrics", []), "id", "metric")
        ratchet(base_spec.get("slices", []), spec.get("slices", []), "name", "slice")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identifier = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        value = sum(a.values()) / len(a) if a else None
        failed = value is None or set(a) != set(b)
        note = "missing/mismatched slice" if failed else ""
        if value is not None and "min" in entry and value < entry["min"]:
            failed = True
        if entry.get("no_significant_drop") and a and set(a) == set(b):
            keys = sorted(a)
            # With one item there is no resampling uncertainty to estimate;
            # the observed one-item paired difference is a degenerate interval.
            if len(keys) == 1:
                d = lo = hi = a[keys[0]] - b[keys[0]]
            else:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                  n_resamples=bs.get("n_resamples", 1000),
                                                  rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            failed |= hi < 0
        if failed and entry.get("blocking"):
            blocked.append(identifier)
        verdict = "BLOCK" if failed and entry.get("blocking") else "warn" if failed else "ok"
        lines.append(f"  {identifier:<40} {value!s:<8} {note:<28} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
