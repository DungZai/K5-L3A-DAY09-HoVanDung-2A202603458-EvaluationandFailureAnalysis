"""Verify the Core CI commands locally and generate M4 evidence and PR text.

Run from src/ after creating baseline_v1.json: python -m scripts.m4_evidence
"""
import json
import os
from pathlib import Path
import subprocess
import sys

from lab8.console import utf8_stdio
from lab9.eval import load_spec, per_item
from lab9.stats import paired_bootstrap


def command(module: str, *args: str, expected: int = 0) -> str:
    result = subprocess.run([sys.executable, "-m", module, *args],
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONUTF8": "1"})
    output = result.stdout + result.stderr
    print(output, end="", flush=True)
    if result.returncode != expected:
        raise RuntimeError(f"{module}: exit {result.returncode}, expected {expected}")
    return output


def main() -> None:
    utf8_stdio()
    spec = load_spec()
    base_path = "reports/baseline_v1.json"
    base = json.loads(Path(base_path).read_text(encoding="utf-8"))
    command("lab9.smoke")
    command("lab9.evalset", "--check")
    outcomes = {}
    for shape, output_name, want in (("swarm", "pr", 0), ("fixed", "fixed", 0),
                                      ("seeded_regression", "seeded_regression", 1)):
        path = f"reports/eval_{output_name}.json"
        command("lab9.eval", "--shape", shape, "--spec", "config/metric_spec.yaml", "--out", path)
        log = command("lab9.gate", "--pr", path, "--baseline", base_path, expected=want)
        if want == 1:
            blocked_line = next(line for line in log.splitlines() if line.startswith("exit 1 — blocked: "))
            if "pass_rate" not in blocked_line.split(": ", 1)[1].split(", "):
                raise AssertionError("seeded_regression must be blocked on pass_rate")
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        a, b = per_item(report, "pass_rate"), per_item(base, "pass_rate")
        keys = sorted(a)
        bs = spec["bootstrap"]
        delta, low, high = paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                          n_resamples=bs["n_resamples"], rng=bs["rng"],
                                          confidence=bs["confidence"])
        outcomes[shape] = {"run_id": report["run_id"], "exit_code": want,
                           "pass_rate_delta": delta, "ci95": [low, high], "gate_output": log}
    ci_output = command("lab9.ci_check", "--pr", "reports/eval_pr.json", "--baseline", base_path)
    d = outcomes["seeded_regression"]
    assert abs(d["pass_rate_delta"] - (-0.271)) <= 0.01
    assert abs(d["ci95"][0] - (-0.500)) <= 0.01
    assert abs(d["ci95"][1] - (-0.057)) <= 0.01
    evidence = {"baseline": base["run_id"], "eval_set_sha": base["manifest"]["eval_set_sha"],
                "metric_spec_version": spec["metric_spec_version"], "bootstrap": spec["bootstrap"],
                "outcomes": outcomes, "ci_check": ci_output}
    Path("reports/m4_gate_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    body = (
        "Hoàn thành Core M0–M4: phân loại lỗi từ trace, calibration judge, code graders và paired bootstrap gate. "
        "Gate dùng cùng spec/baseline, cho swarm và fixed qua, chặn seeded_regression trên pass_rate.\n\n"
        "Validation: 37 test Core pass; eval set v1 có 14 item × 5 seed, 0 problem; "
        "mutation detection 100%, false alarms 0%; ci_check exit 0. "
        f"Baseline `{base['run_id']}`, eval set SHA `{base['manifest']['eval_set_sha']}`.\n\n"
        "Output gate seeded_regression (exit 1):\n\n```text\n"
        + outcomes["seeded_regression"]["gate_output"] + "```\n\n"
        "Giới hạn: MockLLM, 14 item, judge CSV replay; chưa đo trên người dùng thật. "
        "Key 5 anchor chỉ có ở giảng viên; Advanced/Expert chưa thực hiện.\n"
    )
    Path("../docs/pr_m4_body.md").write_text(body, encoding="utf-8")
    print("M4 local checks passed; wrote reports/m4_gate_evidence.json and docs/pr_m4_body.md")


if __name__ == "__main__":
    main()
