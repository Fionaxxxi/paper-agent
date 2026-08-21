from __future__ import annotations

import argparse
import json
from pathlib import Path

from evolution.adapters import analyzer_ab_scorecards, analyzer_baseline_failures
from evolution.pipeline import run_evolution_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="将真实 Research Analyzer A/B 接入受控策略进化门控")
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/evolution/real_analyzer_ab"))
    parser.add_argument("--registry", type=Path, default=Path("outputs/evolution/strategy_versions.json"))
    args = parser.parse_args()
    source = json.loads(args.report.resolve().read_text(encoding="utf-8"))
    if source.get("mode") != "online_ab":
        raise ValueError("只接受真实 online_ab 报告，不能使用 offline_contract")
    baseline, candidate = analyzer_ab_scorecards(source)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    failures_path = output_dir / "real_baseline_failures.json"
    scorecards_path = output_dir / "real_scorecards.json"
    failures_path.write_text(json.dumps(analyzer_baseline_failures(source), ensure_ascii=False, indent=2), encoding="utf-8")
    scorecards_path.write_text(json.dumps({
        "baseline": baseline.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    result = run_evolution_cycle(
        failure_sources=[failures_path],
        scorecards_path=scorecards_path,
        output_dir=output_dir,
        registry_path=args.registry.resolve(),
    )
    print(json.dumps({
        "mode": "real_online_ab",
        "baseline_pass_rate_pct": baseline.pass_rate_pct,
        "candidate_pass_rate_pct": candidate.pass_rate_pct,
        "baseline_average_tokens": baseline.average_tokens,
        "candidate_average_tokens": candidate.average_tokens,
        "baseline_p95_latency_seconds": baseline.p95_latency_seconds,
        "candidate_p95_latency_seconds": candidate.p95_latency_seconds,
        "decision": result["promotion_decision"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
