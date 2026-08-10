"""Validate immutable image evidence before Azure environment promotion."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
VERSION_PATTERN = re.compile(r"^build-[1-9][0-9]*$")
DIGEST_PATTERN = re.compile(
    r"^(?P<registry>[a-z0-9][a-z0-9.-]*\.azurecr\.io)/"
    r"(?P<repository>[a-z0-9][a-z0-9._/-]*)@sha256:[0-9a-f]{64}$"
)


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    commit: str
    version: str
    api_image: str
    ui_image: str


def _required_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"manifest field {name!r} must be a non-empty string")
    return value


def validate_manifest(
    path: Path, *, expected_commit: str, expected_registry: str
) -> ReleaseManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("release manifest must be a JSON object")
    if set(payload) != {"commit", "version", "apiImage", "uiImage"}:
        raise ValueError("release manifest contains missing or unexpected fields")

    commit = _required_string(payload, "commit")
    version = _required_string(payload, "version")
    api_image = _required_string(payload, "apiImage")
    ui_image = _required_string(payload, "uiImage")
    if not COMMIT_PATTERN.fullmatch(commit) or commit != expected_commit:
        raise ValueError("release manifest commit does not match requested commit")
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("release manifest version is invalid")

    expected_repositories = {
        api_image: "industrial-copilot-api",
        ui_image: "industrial-copilot-ui",
    }
    for image, expected_repository in expected_repositories.items():
        match = DIGEST_PATTERN.fullmatch(image)
        if match is None:
            raise ValueError("image reference must use an immutable ACR SHA-256 digest")
        if match.group("registry") != expected_registry:
            raise ValueError("image registry does not match the selected environment")
        if match.group("repository") != expected_repository:
            raise ValueError(
                f"unexpected image repository: {match.group('repository')}"
            )

    return ReleaseManifest(commit, version, api_image, ui_image)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-registry", required=True)
    arguments = parser.parse_args()
    manifest = validate_manifest(
        arguments.manifest,
        expected_commit=arguments.expected_commit,
        expected_registry=arguments.expected_registry,
    )
    output_path = os.getenv("GITHUB_OUTPUT")
    output = (
        f"api_image={manifest.api_image}\n"
        f"ui_image={manifest.ui_image}\n"
        f"build_version={manifest.version}\n"
    )
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output_file:
            output_file.write(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
