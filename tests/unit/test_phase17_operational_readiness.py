"""Repository contracts for Phase 17 operational readiness."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION_SHA = re.compile(r"uses:\s+[^\s@]+@[0-9a-f]{40}(?:\s+#.*)?$")


def test_staging_acceptance_workflow_is_protected_and_complete() -> None:
    content = (ROOT / ".github/workflows/staging-acceptance.yml").read_text(
        encoding="utf-8"
    )
    action_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("uses:")
    ]

    assert action_lines and all(ACTION_SHA.fullmatch(line) for line in action_lines)
    assert "environment: staging" in content
    assert "id-token: write" in content
    assert "alembic current --check-heads" in content
    assert "scripts.index_documents --target azure" in content
    assert "scripts.run_evaluation" in content
    assert "operator_accepted" in content
    assert "rollback_rehearsed" in content
    assert "staging-acceptance.json" in content


def test_production_requires_acceptance_for_the_same_commit() -> None:
    content = (ROOT / ".github/workflows/deploy-prod.yml").read_text(encoding="utf-8")

    assert "staging_acceptance_run_id:" in content
    assert "staging-acceptance-${{ inputs.verified_commit }}" in content
    assert '--expected-commit "${{ inputs.verified_commit }}"' in content
    assert "needs: staging-readiness" in content


def test_required_operational_runbooks_exist_and_have_stop_conditions() -> None:
    required = {
        "incident-response.md": "First 15 minutes",
        "rollback.md": "Abort conditions",
        "database-recovery.md": "potentially destructive",
        "search-reindex.md": "Failure and rollback",
        "staging-readiness.md": "Cost and capacity review",
    }
    operations = ROOT / "docs/operations"

    for filename, contract in required.items():
        content = (operations / filename).read_text(encoding="utf-8")
        assert contract in content
