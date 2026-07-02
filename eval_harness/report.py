from typing import Any, Dict, List


def print_case_result(name: str, passed: bool, errors: List[str]) -> None:
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {name}")

    if errors:
        for error in errors:
            print(f"  - {error}")


def print_summary(results: List[Dict[str, Any]]) -> None:
    total = len(results)
    passed = sum(1 for item in results if item.get("passed"))
    failed = total - passed

    print("\n=== Eval Summary ===")
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")