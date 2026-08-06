"""Static and opt-in runtime checks for the local container stack."""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKER = shutil.which("docker")
RUN_CONTAINER_SMOKE = os.getenv("RUN_CONTAINER_SMOKE") == "1"


def run_compose(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "dockerfile", [ROOT / "Dockerfile", ROOT / "frontend/Dockerfile"]
)
def test_images_have_non_root_runtime_and_healthcheck(dockerfile: Path) -> None:
    content = dockerfile.read_text(encoding="utf-8")

    assert " AS builder" in content
    assert " AS runtime" in content
    assert "USER 10001:10001" in content
    assert "HEALTHCHECK" in content
    assert "--frozen --no-dev" in content


def test_compose_declares_ordered_local_stack() -> None:
    content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    for service in ("postgres:", "database-init:", "api:", "ui:"):
        assert service in content
    assert "condition: service_healthy" in content
    assert "condition: service_completed_successfully" in content
    assert "RUNTIME_MODE: mock" in content
    assert "COPILOT_UI_API_BASE_URL: http://api:8000" in content


@pytest.mark.skipif(DOCKER is None, reason="Docker is not installed")
def test_compose_configuration_is_valid() -> None:
    run_compose("config", "--quiet")


@pytest.fixture
def running_stack() -> Iterator[None]:
    run_compose("up", "--build", "--wait")
    try:
        yield
    finally:
        run_compose("down", "--volumes")


@pytest.mark.skipif(
    not RUN_CONTAINER_SMOKE,
    reason="set RUN_CONTAINER_SMOKE=1 to build and run the container stack",
)
def test_local_stack_starts_non_root_and_ui_reaches_api(
    running_stack: None,
) -> None:
    del running_stack
    with urllib.request.urlopen("http://127.0.0.1:8000/ready", timeout=5) as response:
        assert response.status == 200
    with urllib.request.urlopen(
        "http://127.0.0.1:8501/_stcore/health", timeout=5
    ) as response:
        assert response.status == 200

    assert run_compose("exec", "-T", "api", "id", "-u").stdout.strip() == "10001"
    assert run_compose("exec", "-T", "ui", "id", "-u").stdout.strip() == "10001"
    internal_health = run_compose(
        "exec",
        "-T",
        "ui",
        "python",
        "-c",
        (
            "import urllib.request; "
            "print(urllib.request.urlopen('http://api:8000/health').status)"
        ),
    )
    assert internal_health.stdout.strip() == "200"
