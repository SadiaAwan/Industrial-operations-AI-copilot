"""Security contracts for Phase 15 image publication workflows."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    ROOT / ".github/workflows/security.yml",
    ROOT / ".github/workflows/publish-images.yml",
)
ACTION_SHA = re.compile(r"uses:\s+[^\s@]+@[0-9a-f]{40}(?:\s+#.*)?$")


def test_supply_chain_actions_are_pinned_to_commit_sha() -> None:
    for workflow in WORKFLOWS:
        action_lines = [
            line.strip()
            for line in workflow.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("uses:")
        ]
        assert action_lines
        assert all(ACTION_SHA.fullmatch(line) for line in action_lines)


def test_publication_requires_verified_main_commit_and_oidc() -> None:
    workflow = WORKFLOWS[1].read_text(encoding="utf-8")

    assert "workflow_run:" in workflow
    assert "workflows: [CI]" in workflow
    assert "branches: [main]" in workflow
    assert "conclusion == 'success'" in workflow
    assert "id-token: write" in workflow
    assert "AZURE_CLIENT_SECRET" not in workflow
    assert "az acr login --name" in workflow


def test_images_are_scanned_and_manifested_before_deployment() -> None:
    workflow = WORKFLOWS[1].read_text(encoding="utf-8")
    scan_position = workflow.index("aquasecurity/trivy-action")
    push_position = workflow.index('docker push "$api_repository:$BUILD_SHA"')

    assert scan_position < push_position
    assert "severity: HIGH,CRITICAL" in workflow
    assert "format: spdx-json" in workflow
    assert "release-manifest.json" in workflow
    assert "apiImage: $apiImage" in workflow
    assert "uiImage: $uiImage" in workflow
