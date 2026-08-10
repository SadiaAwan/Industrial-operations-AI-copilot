"""Promotion and rollback contracts for Phase 15 Azure delivery."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMOTION_WORKFLOW = ROOT / ".github/workflows/_promote-azure.yml"
ENTRY_WORKFLOWS = {
    "development": ROOT / ".github/workflows/deploy-dev.yml",
    "staging": ROOT / ".github/workflows/deploy-staging.yml",
    "production": ROOT / ".github/workflows/deploy-prod.yml",
}
ACTION_SHA = re.compile(r"uses:\s+[^\s@]+@[0-9a-f]{40}(?:\s+#.*)?$")


def test_all_environments_call_the_same_promotion_workflow() -> None:
    for environment, path in ENTRY_WORKFLOWS.items():
        content = path.read_text(encoding="utf-8")
        assert "uses: ./.github/workflows/_promote-azure.yml" in content
        assert f"environment: {environment}" in content
        assert "verified_commit:" in content
        assert "publish_run_id:" in content
        assert "change_reason:" in content


def test_promotion_uses_oidc_protected_environments_and_digests() -> None:
    content = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
    action_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("uses:") and "./.github" not in line
    ]

    assert action_lines
    assert all(ACTION_SHA.fullmatch(line) for line in action_lines)
    assert "id-token: write" in content
    assert "environment: ${{ inputs.environment }}" in content
    assert "AZURE_CLIENT_SECRET" not in content
    assert "@${API_SOURCE#*@}" in content
    assert "@${UI_SOURCE#*@}" in content
    assert 'apiImageReference="$API_IMAGE"' in content
    assert 'uiImageReference="$UI_IMAGE"' in content


def test_deployment_is_planned_migrated_verified_and_audited() -> None:
    content = PROMOTION_WORKFLOW.read_text(encoding="utf-8")

    assert content.index("az deployment sub what-if") < content.index(
        "az deployment sub create"
    )
    assert "alembic upgrade head" in content
    assert '"https://$api_fqdn/health"' in content
    assert '"https://$ui_fqdn/_stcore/health"' in content
    assert "deployment-evidence.json" in content


def test_bicep_accepts_separate_immutable_image_references() -> None:
    main = (ROOT / "infra/main.bicep").read_text(encoding="utf-8")
    subscription = (ROOT / "infra/subscription.bicep").read_text(encoding="utf-8")

    for content in (main, subscription):
        assert "param apiImageReference string" in content
        assert "param uiImageReference string" in content
        assert "param imageTag string" not in content
    assert "image: apiImageReference" in main
    assert "image: uiImageReference" in main
