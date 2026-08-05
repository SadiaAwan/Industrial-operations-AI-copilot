"""Immutable prompt registry and evaluation-gated promotion workflow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.comparison import EvaluationComparison, compare_reports
from app.evaluation.gates import ReleaseGateSummary, enforce_release_gate
from app.evaluation.models import EvaluationReport


class PromptLifecycleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class PromptVersion(PromptLifecycleModel):
    prompt_id: str = Field(min_length=1)
    version: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]+$")
    file: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["active", "candidate", "retired"]


class PromptManifest(PromptLifecycleModel):
    prompts: tuple[PromptVersion, ...] = Field(min_length=1)


class PromptEvaluationComparison(PromptLifecycleModel):
    prompt_id: str
    baseline_version: str
    candidate_version: str
    evaluation: EvaluationComparison
    gate: ReleaseGateSummary


class PromptRegistry:
    def __init__(self, manifest_path: Path) -> None:
        self._root = manifest_path.resolve().parent
        self._manifest = PromptManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        keys = [(item.prompt_id, item.version) for item in self._manifest.prompts]
        if len(keys) != len(set(keys)):
            raise ValueError("prompt manifest contains duplicate versions")

    def get(self, prompt_id: str, version: str) -> PromptVersion:
        for prompt in self._manifest.prompts:
            if prompt.prompt_id == prompt_id and prompt.version == version:
                return prompt
        raise LookupError(f"unknown prompt version: {prompt_id}@{version}")

    def content(self, prompt_id: str, version: str) -> str:
        prompt = self.get(prompt_id, version)
        path = (self._root / prompt.file).resolve()
        if self._root not in path.parents:
            raise ValueError("prompt path escapes registry directory")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != prompt.sha256:
            raise ValueError(f"prompt digest mismatch: {prompt_id}@{version}")
        return content.decode("utf-8")

    def fingerprint(self) -> str:
        payload = [item.model_dump(mode="json") for item in self._manifest.prompts]
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


def evaluate_prompt_candidate(
    *,
    baseline: PromptVersion,
    candidate: PromptVersion,
    baseline_report: EvaluationReport,
    candidate_report: EvaluationReport,
    tolerance: float = 0.0,
) -> PromptEvaluationComparison:
    """Block prompt promotion unless quality gates and regression gates pass."""

    if baseline.prompt_id != candidate.prompt_id:
        raise ValueError("prompt comparison requires the same prompt_id")
    if baseline.version == candidate.version:
        raise ValueError("prompt comparison requires different versions")
    if candidate.status != "candidate":
        raise ValueError("only candidate prompt versions can be evaluated")
    comparison = compare_reports(baseline_report, candidate_report, tolerance=tolerance)
    gate = enforce_release_gate(candidate_report, comparison)
    return PromptEvaluationComparison(
        prompt_id=candidate.prompt_id,
        baseline_version=baseline.version,
        candidate_version=candidate.version,
        evaluation=comparison,
        gate=gate,
    )
