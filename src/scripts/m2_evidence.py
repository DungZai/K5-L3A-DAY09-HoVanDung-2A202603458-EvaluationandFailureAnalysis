"""Generate M2 calibration evidence from unchanged public CSVs; run from src/."""
import hashlib
import json
from pathlib import Path

from lab9.judge import FLOORS, calibrate


def main() -> None:
    sources = {name: Path(f"data/eval/judge_{name}_public.csv") for name in ("tone", "helpful")}
    fingerprints = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [*sources.values(), Path("lab9/stats.py"), Path("lab9/judge.py")]}
    digest = hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:12]
    evidence = {"run_id": f"J-M2-{digest}", "backend": "CSV replay",
                "positive_class": "FAIL", "floors": FLOORS,
                "sha256": fingerprints,
                "results": {name: calibrate(path) for name, path in sources.items()}}
    out = Path("../docs/m2_judge_evidence.json")
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(evidence["run_id"])
    for name, result in evidence["results"].items():
        print(name, {k: v for k, v in result.items() if k != "disagreements"})
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
