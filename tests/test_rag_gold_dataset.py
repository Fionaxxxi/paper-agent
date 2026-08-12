import json
from pathlib import Path

from eval_harness.rag_eval_models import load_rag_dataset
from local_rag.parser import PyPDFPageParser
from scripts.build_rag_gold_dataset import build_dataset


GOLD_PATH = Path("eval_harness/datasets/rag_gold_v1.json")
PAPERS_DIR = Path("data/papers")


def test_rag_gold_v1_has_balanced_corpus_and_question_coverage():
    dataset = load_rag_dataset(GOLD_PATH)
    document_ids = {span.document_id for case in dataset.cases for span in case.evidence}
    categories = {case.category for case in dataset.cases}
    difficulties = {case.difficulty for case in dataset.cases}

    assert len(dataset.cases) == 16
    assert len(document_ids) == 8
    assert {"method", "experiment", "memory", "limitation", "planning"} <= categories
    assert difficulties == {"simple", "complex"}


def test_rag_gold_v1_evidence_is_present_on_declared_pdf_page():
    dataset = load_rag_dataset(GOLD_PATH)
    parser = PyPDFPageParser()
    page_cache = {}

    for case in dataset.cases:
        for evidence in case.evidence:
            source = Path(evidence.source_path)
            if source not in page_cache:
                page_cache[source] = parser.parse(source, evidence.document_id)
            page = page_cache[source][evidence.page_start - 1]
            assert evidence.quote in page.text, case.id
            assert page.page_number == evidence.page_start


def test_rag_gold_builder_reproduces_committed_dataset(tmp_path):
    generated = build_dataset(PAPERS_DIR, tmp_path / "rag_gold_v1.json")
    expected = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    actual = json.loads(generated.read_text(encoding="utf-8"))
    assert actual == expected
