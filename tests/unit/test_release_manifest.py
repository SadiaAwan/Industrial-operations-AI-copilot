import json
from pathlib import Path

import pytest

from scripts.validate_release_manifest import validate_manifest

COMMIT = "a" * 40
REGISTRY = "industrialdev.azurecr.io"


def write_manifest(path: Path, **overrides: str) -> None:
    payload = {
        "commit": COMMIT,
        "version": "build-1234",
        "apiImage": f"{REGISTRY}/industrial-copilot-api@sha256:{'b' * 64}",
        "uiImage": f"{REGISTRY}/industrial-copilot-ui@sha256:{'c' * 64}",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_accepts_complete_manifest_with_expected_digest_images(tmp_path: Path) -> None:
    manifest_path = tmp_path / "release-manifest.json"
    write_manifest(manifest_path)

    manifest = validate_manifest(
        manifest_path, expected_commit=COMMIT, expected_registry=REGISTRY
    )

    assert manifest.commit == COMMIT
    assert manifest.api_image.endswith("b" * 64)
    assert manifest.ui_image.endswith("c" * 64)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"commit": "d" * 40}, "commit does not match"),
        ({"version": "latest"}, "version is invalid"),
        ({"apiImage": "industrialdev.azurecr.io/api:latest"}, "immutable"),
        (
            {"uiImage": ("other.azurecr.io/industrial-copilot-ui@sha256:" + "c" * 64)},
            "registry does not match",
        ),
    ],
)
def test_rejects_untrusted_release_evidence(
    tmp_path: Path, overrides: dict[str, str], message: str
) -> None:
    manifest_path = tmp_path / "release-manifest.json"
    write_manifest(manifest_path, **overrides)

    with pytest.raises(ValueError, match=message):
        validate_manifest(
            manifest_path, expected_commit=COMMIT, expected_registry=REGISTRY
        )
