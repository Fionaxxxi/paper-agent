from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_docker_image_uses_non_root_user_and_healthcheck() -> None:
    dockerfile = _read("Dockerfile")

    assert "USER paperagent" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "app.api:app" in dockerfile


def test_dockerignore_excludes_secrets_and_large_runtime_artifacts() -> None:
    ignored = set(_read(".dockerignore").splitlines())

    assert ".env" in ignored
    assert "data/cache" in ignored
    assert "data/memory" in ignored
    assert "data/papers/*.pdf" in ignored
    assert "outputs" in ignored


def test_ci_is_deterministic_and_builds_the_runtime_image() -> None:
    workflow = _read(".github/workflows/ci.yml")

    assert 'OPENAI_API_KEY: ""' in workflow
    assert 'REASON_WITH_LLM: "false"' in workflow
    assert 'LANGGRAPH_CHECKPOINT_ENABLED: "false"' in workflow
    assert "node --check app/static/app.js" in workflow
    assert "docker build --tag paper-agent:ci ." in workflow


def test_compose_persists_data_and_checks_service_health() -> None:
    compose = _read("docker-compose.yml")

    assert "./data:/app/data" in compose
    assert "./logs:/app/logs" in compose
    assert "http://127.0.0.1:8000/health" in compose
