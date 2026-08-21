from __future__ import annotations

import argparse
import json
from pathlib import Path

from evolution.pipeline import run_evolution_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 PaperAgent 受控策略进化离线闭环")
    parser.add_argument("--failures", nargs="+", type=Path, default=[Path("eval_harness/datasets/evolution_failures_v1.json")])
    parser.add_argument("--scorecards", type=Path, default=Path("eval_harness/datasets/evolution_scorecards_v1.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/evolution"))
    parser.add_argument("--registry", type=Path, default=Path("outputs/evolution/strategy_versions.json"))
    args = parser.parse_args()
    report = run_evolution_cycle(
        failure_sources=[path.resolve() for path in args.failures],
        scorecards_path=args.scorecards.resolve(),
        output_dir=args.output_dir.resolve(),
        registry_path=args.registry.resolve(),
    )
    print(json.dumps({
        "failure_count": report["failure_dataset"]["summary"]["failure_count"],
        "candidate_count": len(report["strategy_candidates"]),
        "promotion_status": report["promotion_decision"]["status"],
        "gate_passed": report["promotion_decision"]["gate_passed"],
        "auto_applied": report["promotion_decision"]["auto_applied"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
