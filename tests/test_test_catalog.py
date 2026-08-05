import ast
from pathlib import Path

from scripts.test_case_catalog import TEST_CASE_CATALOG


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _discover_test_functions() -> set[str]:
    discovered: set[str] = set()
    for test_file in sorted((PROJECT_ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
        relative_path = test_file.relative_to(PROJECT_ROOT).as_posix()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    discovered.add(f"{relative_path}::{node.name}")
    return discovered


def test_catalog_exactly_covers_all_test_functions():
    discovered = _discover_test_functions()
    catalog_keys = set(TEST_CASE_CATALOG)

    assert catalog_keys == discovered, (
        f"missing descriptions: {sorted(discovered - catalog_keys)}; "
        f"stale descriptions: {sorted(catalog_keys - discovered)}"
    )
    for key, description in TEST_CASE_CATALOG.items():
        assert all(description.values()), f"incomplete test description: {key}"
