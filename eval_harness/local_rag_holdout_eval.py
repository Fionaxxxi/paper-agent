"""在冻结术语表之后运行独立保留集 A/B。"""

from pathlib import Path

from eval_harness.local_rag_rewrite_ab import run_ab


if __name__ == "__main__":
    report = run_ab(
        Path("outputs/local_rag/bm25_rewrite_holdout.json"),
        Path("eval_harness/datasets/rag_holdout_v1.json"),
        "independent_holdout_generalization_evidence",
    )
    print(report["comparison"])
    print(report["outcomes"])
