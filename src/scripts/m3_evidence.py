"""Run the M3 graders and write reproducible reports, never hand-edit them.

From src/: python -m scripts.m3_evidence
"""
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9 import variants
from lab9.eval import SPEC, load_spec, run_eval
from lab9.evalset import sha12
from lab9.graders import GRADERS
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape


def main() -> None:
    utf8_stdio()
    variants.register()
    SHAPES["m3_misreport"] = make_shape("m3_misreport", {"no_override", "misreport"})
    spec = load_spec()
    reports = {}
    Path("reports").mkdir(exist_ok=True)
    for shape in ("fixed", "seeded_regression", "m3_misreport"):
        report = run_eval(shape, spec)
        if report["evaluator_failures"]:
            raise RuntimeError(report["evaluator_failures"])
        reports[shape] = report
        path = Path(f"reports/eval_{shape}.json")
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(report["run_id"], report["metrics"], flush=True)

    # Same definition as lab9.mutation.detect: explanations exclude pass_rate.
    bad_values = {m["id"]: "max" in m.get("threshold", {}) for m in spec["metrics"]
                  if m["id"] in GRADERS and m["id"] != "pass_rate"}
    def flagged(row):
        return any(row.get(k) is bad for k, bad in bad_values.items())
    broken = [r for r in reports["seeded_regression"]["rows"] if r["pass_rate"] is False]
    detected = sum(flagged(r) for r in broken)
    false_alarms = sum(flagged(r) for r in reports["fixed"]["rows"])
    fm08 = [r for r in reports["m3_misreport"]["rows"] if r["reply_amount_correct"] is False]
    assert broken and detected / len(broken) >= 0.8
    assert false_alarms / len(reports["fixed"]["rows"]) <= 0.1
    assert {(r["item_id"], r["seed"]) for r in fm08} == {
        (item, seed) for item in ("E-008", "E-014") for seed in spec["seeds"]}
    evidence = {
        "metric_spec_version": spec["metric_spec_version"], "spec_sha": sha12(SPEC),
        "reports": {shape: {"path": f"reports/eval_{shape}.json", "run_id": rep["run_id"],
                             "metrics": rep["metrics"]} for shape, rep in reports.items()},
        "detection": {"failing_trials": len(broken), "detected": detected,
                      "rate": detected / len(broken)},
        "false_alarms": {"trials": len(reports["fixed"]["rows"]), "flagged": false_alarms,
                         "rate": false_alarms / len(reports["fixed"]["rows"])},
        "fm08_flagged": len(fm08),
        "trace_case": {shape: investigate(shape, "C-002", 11)
                       for shape in ("seeded_regression", "fixed")},
    }
    out = Path("../docs/m3_grader_evidence.json")
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"detection {detected}/{len(broken)}; false alarms {false_alarms}/70; FM-08 flags {len(fm08)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
