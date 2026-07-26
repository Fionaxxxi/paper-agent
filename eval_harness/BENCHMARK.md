# Offline Capability Benchmark

This benchmark compares the current implementation with explicit legacy
strategies without calling an LLM, arXiv, or any other network service.

## Run

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.benchmark
```

The default report is written to:

```text
eval_harness/reports/offline_benchmark.json
```

Use a different output path when keeping multiple runs:

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.benchmark `
  --output eval_harness/reports/candidate.json
```

## Profiles

```text
baseline
├─→ all inputs are treated as research requests
├─→ retrieval always uses one query
├─→ multi-query documents are concatenated without deduplication
└─→ low retrieval scores never trigger a retry

candidate
├─→ uses the current Intent Router
├─→ uses the current rule-based Query Planner
├─→ uses the current Result Merger
└─→ uses the current retrieval retry router
```

## Metric interpretation

Higher is better:

- `accuracy_pct`
- `plan_accuracy_pct`
- `route_accuracy_pct`
- `local_response_count`
- `estimated_llm_calls_avoided`

Lower is better:

- `research_false_block_count`
- `unnecessary_simple_queries`
- `remaining_duplicate_count`

Context-dependent:

- `total_planned_queries`
- `average_query_count`
- `retry_count`
- `documents_removed`

These context-dependent metrics must be reviewed together with accuracy.
More queries can improve coverage while also increasing latency and cost.

## Scope

The offline benchmark measures deterministic routing and data-processing
behavior. It does not yet measure:

- real model input and output tokens;
- answer groundedness or hallucination rate;
- live arXiv recall and latency;
- LLM answer quality;
- monetary cost.

Those measurements belong in a separate online benchmark so offline CI
remains stable and free of API cost.
