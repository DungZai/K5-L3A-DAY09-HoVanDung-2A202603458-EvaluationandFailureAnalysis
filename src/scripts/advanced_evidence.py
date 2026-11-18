"""Generate Advanced/Expert reports, A/A, mutation and trap CLI evidence.

Run from src/: python -m scripts.advanced_evidence
Reports are generated from real shape runs, never filled in or edited by hand.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9 import gate, variants
from lab9.eval import load_spec, load_world, make_task, run_eval
from lab9.evalset import load_jsonl
from lab9.variant_agent import make_shape

SPEC = Path("config/metric_spec_v2.yaml")


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cli(module, *args, expected=0):
    result = subprocess.run([sys.executable, "-m", module, *map(str, args)],
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONUTF8": "1"})
    print(result.stdout, end="", flush=True)
    if result.returncode != expected:
        raise RuntimeError(f"{module} exit {result.returncode}: {result.stderr}")
    return result.stdout


def main():
    utf8_stdio()
    variants.register()
    spec = load_spec(SPEC)
    reports = {}
    for shape in ("swarm", "fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression"):
        print(f"Evaluating {shape} ...", flush=True)
        report = run_eval(shape, spec)
        if report["evaluator_failures"]:
            raise RuntimeError(report["evaluator_failures"])
        path = "reports/baseline_v2.json" if shape == "swarm" else f"reports/v2/eval_{shape}.json"
        write(path, report)
        # The trap command in README uses this path.
        if shape == "slice_regression":
            write("reports/eval_slice_regression.json", report)
        reports[shape] = report
        print(report["run_id"], report["metrics"], flush=True)
    print("Running official A/A CLI ...", flush=True)
    aa = cli("lab9.mutation", "--spec", SPEC, "--aa", "66,77,88,99,110")
    print("Running official mutation CLI ...", flush=True)
    mutation = cli("lab9.mutation", "--spec", SPEC, "--baseline", "reports/baseline_v2.json")
    print("Running official traps CLI ...", flush=True)
    traps = cli("lab9.traps", "--pr", "reports/eval_slice_regression.json",
                "--baseline", "reports/baseline_v2.json", "--spec", SPEC)
    trap_logs = {}
    for path in sorted(Path("reports/traps").glob("*.json")):
        args = ["--pr", path, "--baseline", "reports/baseline_v2.json", "--spec", SPEC]
        loose = path.with_suffix(".spec.yaml")
        if loose.exists():
            args = ["--pr", path, "--baseline", "reports/baseline_v2.json", "--spec", loose, "--base-spec", SPEC]
        trap_logs[path.stem] = cli("lab9.gate", *args, expected=1)
        if "INTEGRITY" not in trap_logs[path.stem]:
            raise AssertionError(f"trap must be rejected for integrity: {path}")
    base = reports["swarm"]
    decisions = {}
    for name, report in reports.items():
        blocked, lines = gate.check(report, base, spec, spec)
        decisions[name] = {"blocked": blocked, "lines": lines}
    assert not decisions["swarm"]["blocked"]
    assert "slice:money_movement/pass_rate" in decisions["slice_regression"]["blocked"]
    assert "pass_hat_5" in decisions["flaky_regression"]["blocked"]
    # An unseen combination with no model_override event must still be caught
    # through outcomes. The grader/gate never look at its name or bug switches.
    quiet_name = "validation_quiet_ticket"
    SHAPES[quiet_name] = make_shape(quiet_name, {"quiet_override"})
    quiet = run_eval(quiet_name, spec)
    write("reports/v2/eval_quiet_ticket.json", quiet)
    quiet_blocked, quiet_lines = gate.check(quiet, base, spec)
    assert quiet_blocked and quiet["metrics"]["db_fact_kept"] == 1.0
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="lab9-v2-evidence-", ignore_cleanup_errors=True) as tmp:
        task = make_task("fixed", world, claims, labels, Path(tmp))
        cross = {claim: task({"claim_id": claim, "seed": 11}) for claim in ("C-110", "C-113", "C-114")}
    assert all(trial["lab8_pass"] and trial["result"]["status"] == "escalated" for trial in cross.values())
    coverage = {}
    for item in load_jsonl(Path(spec["eval_set"])):
        for fm in item["failure_modes"]:
            coverage[fm] = coverage.get(fm, 0) + 1
    evidence = {
        "spec": str(SPEC), "baseline": base["run_id"], "manifest": base["manifest"],
        "metrics": {name: report["metrics"] for name, report in reports.items()},
        "run_ids": {name: report["run_id"] for name, report in reports.items()},
        "decisions": decisions, "aa_output": aa, "mutation_output": mutation,
        "traps_output": traps, "trap_gate_outputs": trap_logs, "coverage": coverage,
        "quiet_validation": {"metrics": quiet["metrics"], "blocked": quiet_blocked, "lines": quiet_lines},
        "cross_principal_controls": cross,
    }
    write("reports/advanced_evidence.json", evidence)
    body = ("Hoàn thành M5–M7: eval set v2, slice gate, pass@k/pass^k, integrity và ratchet. "
            "Code xử lý cơ chế/metric thay vì khớp tên variant.\n\n"
            f"Baseline `{base['run_id']}`, SHA `{base['manifest']['eval_set_sha']}`.\n\n"
            "A/A:\n\n```text\n" + aa + "```\n\nMutation:\n\n```text\n" + mutation + "```\n\n"
            "Traps:\n\n```text\n" + traps + "```\n\n")
    for name, output in trap_logs.items():
        body += f"{name}:\n\n```text\n" + output + "```\n\n"
    body += "Giới hạn: MockLLM; 5 seed chưa phát hiện ổn định bug xác suất 1/3; test/variant ẩn chỉ giảng viên có.\n"
    Path("../docs/pr_advanced_body.md").write_text(
        "\n".join(line.rstrip() for line in body.splitlines()) + "\n", encoding="utf-8")
    print("Advanced/Expert evidence generated successfully", flush=True)


if __name__ == "__main__":
    main()
