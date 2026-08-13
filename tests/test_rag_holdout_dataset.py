import json
from pathlib import Path

from eval_harness.rag_eval_models import load_rag_dataset
from local_rag.parser import PyPDFPageParser
from scripts.build_rag_holdout_dataset import build_holdout


HOLDOUT = Path("eval_harness/datasets/rag_holdout_v1.json")
DEVELOPMENT = Path("eval_harness/datasets/rag_gold_v1.json")


def test_holdout_has_ten_cases_and_no_development_evidence_pages():
    holdout, development = load_rag_dataset(HOLDOUT), load_rag_dataset(DEVELOPMENT)
    holdout_pages = {(e.document_id, e.page_start) for case in holdout.cases for e in case.evidence}
    development_pages = {(e.document_id, e.page_start) for case in development.cases for e in case.evidence}
    assert len(holdout.cases) == 10
    assert len({e.document_id for case in holdout.cases for e in case.evidence}) == 8
    assert holdout_pages.isdisjoint(development_pages)


def test_holdout_evidence_is_present_on_declared_pdf_page():
    parser, cache = PyPDFPageParser(), {}
    for case in load_rag_dataset(HOLDOUT).cases:
        evidence = case.evidence[0]; source = Path(evidence.source_path)
        cache.setdefault(source, parser.parse(source, evidence.document_id))
        assert evidence.quote in cache[source][evidence.page_start - 1].text


def test_holdout_builder_reproduces_frozen_json(tmp_path):
    actual = json.loads(build_holdout(Path("data/papers"), tmp_path / "holdout.json").read_text(encoding="utf-8"))
    expected = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    assert actual == expected
