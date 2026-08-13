import json
from pathlib import Path

from eval_harness.local_rag_dense_eval import _chunks
from eval_harness.rag_eval_models import load_rag_dataset
from scripts.build_rag_holdout_v2 import build_holdout_v2

V2=Path("eval_harness/datasets/rag_holdout_v2.json")
V1_PATHS=(Path("eval_harness/datasets/rag_gold_v1.json"),Path("eval_harness/datasets/rag_holdout_v1.json"))


def test_holdout_v2_has_eight_papers_and_no_v1_evidence_pages():
    dataset=load_rag_dataset(V2);pages={(e.document_id,e.page_start) for c in dataset.cases for e in c.evidence};used=set()
    for path in V1_PATHS:
        old=load_rag_dataset(path);used|={(e.document_id,e.page_start) for c in old.cases for e in c.evidence}
    assert len(dataset.cases)==8
    assert len({e.document_id for c in dataset.cases for e in c.evidence})==8
    assert pages.isdisjoint(used)


def test_holdout_v2_quotes_equal_declared_chunks():
    chunks={chunk.chunk_id:chunk for chunk in _chunks(Path("data/papers"))[0]}
    for case in load_rag_dataset(V2).cases:
        evidence=case.evidence[0];chunk=chunks[evidence.chunk_id]
        assert evidence.quote==chunk.text
        assert (evidence.document_id,evidence.page_start)==(chunk.document_id,chunk.page_start)


def test_holdout_v2_builder_reproduces_frozen_json(tmp_path):
    actual=json.loads(build_holdout_v2(Path("data/papers"),tmp_path/"v2.json").read_text(encoding="utf-8"))
    assert actual==json.loads(V2.read_text(encoding="utf-8"))
