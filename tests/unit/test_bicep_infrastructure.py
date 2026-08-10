"""Fast security and topology checks for Phase 14 Bicep assets."""

from __future__ import annotations

import re
from pathlib import Path

INFRA = Path("infra")


def _read(relative_path: str) -> str:
    return (INFRA / relative_path).read_text(encoding="utf-8")


def test_required_azure_resources_are_declared() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in INFRA.rglob("*.bicep")
    )

    for resource_type in (
        "Microsoft.App/containerApps",
        "Microsoft.App/managedEnvironments",
        "Microsoft.ContainerRegistry/registries",
        "Microsoft.DBforPostgreSQL/flexibleServers",
        "Microsoft.Insights/components",
        "Microsoft.KeyVault/vaults",
        "Microsoft.ManagedIdentity/userAssignedIdentities",
        "Microsoft.OperationalInsights/workspaces",
        "Microsoft.Search/searchServices",
        "Microsoft.Storage/storageAccounts",
    ):
        assert resource_type in source


def test_environment_parameter_files_are_separate_and_secret_free() -> None:
    environment_sources = {
        environment: _read(f"environments/{environment}.bicepparam")
        for environment in ("dev", "staging", "prod")
    }

    for environment, source in environment_sources.items():
        assert f"param environment = '{environment}'" in source
        assert f"rg-industrial-ai-{environment}" in source
        assert (
            re.search(r"password\s*=|secret\s*=|token\s*=|apiKey\s*=", source, re.I)
            is None
        )
        assert "@secure" not in source

    assert len(set(environment_sources.values())) == 3


def test_local_authentication_and_public_blob_access_are_disabled() -> None:
    assert "adminUserEnabled: false" in _read("modules/container-registry.bicep")
    assert "disableLocalAuth: true" in _read("modules/ai-search.bicep")
    storage = _read("modules/blob-storage.bicep")
    assert "allowBlobPublicAccess: false" in storage
    assert "allowSharedKeyAccess: false" in storage
    assert "defaultToOAuthAuthentication: true" in storage
    assert "publicAccess: 'None'" in storage
    assert "passwordAuth: 'Disabled'" in _read("modules/postgresql.bicep")


def test_rbac_uses_only_expected_data_plane_roles() -> None:
    access = _read("modules/access-control.bicep")
    expected_role_ids = {
        "7f951dda-4ed3-4680-a7ca-43fe172d538d",  # AcrPull
        "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",  # Blob Data Reader
        "4633458b-17de-408a-b874-0445c86b69e6",  # Key Vault Secrets User
        "1407120a-92aa-4202-b7e9-c0e197c71c8f",  # Search Index Data Reader
    }

    discovered = set(re.findall(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", access))
    assert discovered == expected_role_ids
    assert "Owner" not in access
    assert "Contributor" not in access


def test_production_deploy_requires_what_if_and_environment_gate() -> None:
    entrypoint = Path(".github/workflows/deploy-prod.yml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/_promote-azure.yml").read_text(encoding="utf-8")

    assert "az deployment sub what-if" in workflow
    assert "needs: plan" in workflow
    assert "environment: ${{ inputs.environment }}" in workflow
    assert "uses: azure/login@" in workflow
    assert "environment: production" in entrypoint
    assert "uses: ./.github/workflows/_promote-azure.yml" in entrypoint
    assert "password" not in workflow.casefold()
