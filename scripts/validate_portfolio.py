"""Validate Phase 18 portfolio links, evidence, commands, and secret hygiene."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "docs" / "portfolio"
REQUIRED_FILES = (
    ROOT / "README.md",
    PORTFOLIO / "README.md",
    PORTFOLIO / "architecture.md",
    PORTFOLIO / "demo-guide.md",
    PORTFOLIO / "results-and-lessons.md",
    PORTFOLIO / "limitations.md",
    PORTFOLIO / "roadmap.md",
    PORTFOLIO / "definition-of-done.md",
    PORTFOLIO / "assets" / "reference-latency-cost.svg",
    ROOT / "evaluation" / "reports" / "phase18-reference.json",
)
LINK_PATTERN = re.compile(r"!?\[[^]]*]\(([^)]+)\)")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\b(?:password|client_secret)\s*[:=]\s*[^$<{\s][^\s]*", re.I),
)
REQUIRED_COMMANDS = (
    "docker compose up --build --wait",
    "uv sync --locked --all-groups",
    "uv run ruff check .",
    "uv run mypy app frontend tests evaluation scripts",
    "uv run pytest -q",
    "uv run python -m scripts.run_evaluation",
    "uv run python -m scripts.validate_portfolio",
)


def _local_link_target(document: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().split("#", 1)[0]
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    return (document.parent / target).resolve()


def validate() -> list[str]:
    errors: list[str] = []
    for required in REQUIRED_FILES:
        if not required.exists():
            errors.append(f"missing required portfolio file: {required.relative_to(ROOT)}")

    documents = [ROOT / "README.md", *sorted(PORTFOLIO.rglob("*.md"))]
    for document in documents:
        if not document.exists():
            continue
        content = document.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(content):
            target = _local_link_target(document, raw_target)
            if target is not None and not target.exists():
                errors.append(
                    f"broken local link in {document.relative_to(ROOT)}: {raw_target}"
                )
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(
                    f"possible secret in {document.relative_to(ROOT)}: {pattern.pattern}"
                )

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for command in REQUIRED_COMMANDS:
        if command not in readme:
            errors.append(f"README is missing required command: {command}")

    report_path = ROOT / "evaluation" / "reports" / "phase18-reference.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = {
            "dataset_id": "industrial-copilot-reference",
            "dataset_version": "1.0.0",
            "dataset_sha256": (
                "378d8fda13c4c5600bed3ffcf09a69525fe1bdcc66cfdae11d0a61be13d0370e"
            ),
            "generated_at": "2026-08-12T00:00:00Z",
            "passed": True,
        }
        for key, value in expected.items():
            if report.get(key) != value:
                errors.append(f"evaluation report has unexpected {key}")
        if len(report.get("cases", [])) != 3:
            errors.append("evaluation report must contain three reference cases")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"PORTFOLIO ERROR: {error}")
        return 1
    print("PORTFOLIO VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
