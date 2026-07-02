from eval_harness.cases import CACHE_EVAL_CASE, EVAL_CASES
from eval_harness.report import print_case_result, print_summary
from eval_harness.validators import validate_cache_hit, validate_result
from services.paper_agent_service import paper_agent_service


def run_single_case(case):
    name = case["name"]
    query = case["query"]
    conversation_id = case.get("conversation_id")
    pdf_path = case.get("pdf_path")
    expected = case.get("expected", {})

    try:
        result = paper_agent_service.chat(
            query=query,
            conversation_id=conversation_id,
            pdf_path=pdf_path,
        )

        passed, errors = validate_result(result, expected)

        return {
            "name": name,
            "passed": passed,
            "errors": errors,
            "result": result,
        }

    except Exception as e:
        return {
            "name": name,
            "passed": False,
            "errors": [f"{type(e).__name__}: {e}"],
            "result": None,
        }


def run_cache_case():
    name = CACHE_EVAL_CASE["name"]
    query = CACHE_EVAL_CASE["query"]
    conversation_id = CACHE_EVAL_CASE.get("conversation_id")
    pdf_path = CACHE_EVAL_CASE.get("pdf_path")

    try:
        first_result = paper_agent_service.chat(
            query=query,
            conversation_id=conversation_id,
            pdf_path=pdf_path,
        )

        second_result = paper_agent_service.chat(
            query=query,
            conversation_id=conversation_id,
            pdf_path=pdf_path,
        )

        passed, errors = validate_cache_hit(first_result, second_result)

        return {
            "name": name,
            "passed": passed,
            "errors": errors,
            "result": second_result,
        }

    except Exception as e:
        return {
            "name": name,
            "passed": False,
            "errors": [f"{type(e).__name__}: {e}"],
            "result": None,
        }


def main():
    print("\n=== PaperAgent Eval Harness ===\n")

    results = []

    for case in EVAL_CASES:
        result = run_single_case(case)
        results.append(result)
        print_case_result(
            name=result["name"],
            passed=result["passed"],
            errors=result["errors"],
        )

    cache_result = run_cache_case()
    results.append(cache_result)
    print_case_result(
        name=cache_result["name"],
        passed=cache_result["passed"],
        errors=cache_result["errors"],
    )

    print_summary(results)


if __name__ == "__main__":
    main()