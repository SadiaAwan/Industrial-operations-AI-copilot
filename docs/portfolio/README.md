# Portfolio delivery

This directory is the evidence map for the Industrial AI Operations Copilot.
It separates reproducible repository evidence from deployment claims that need
an environment-specific artifact.

## Delivery map

| Area | Evidence |
| --- | --- |
| Product and onboarding | [Project README](../../README.md) |
| System design | [Architecture](architecture.md) |
| Local walkthrough | [Demo guide](demo-guide.md) |
| Evaluation evidence | [Results and lessons](results-and-lessons.md) |
| Known boundaries | [Limitations](limitations.md) |
| Planned extensions | [Roadmap](roadmap.md) |
| Azure topology and deployment | [Azure deployment runbook](../operations/azure-deployment.md) |
| Operational readiness | [Phase 17 checklist](../operations/phase-17-checklist.md) |
| Completion evidence | [Definition of Done](definition-of-done.md) |

## Evidence policy

- Numbers identify their dataset, version, command, and execution mode.
- Reference evaluation results are deterministic fixtures, not production
  measurements or Azure load-test results.
- Azure deployment is documented and automated, but a deployment is claimed
  only when retained GitHub and Azure artifacts exist for the same commit.
- Screenshots must use synthetic records and exclude credentials, tokens,
  personal data, browser profiles, subscription identifiers, and hidden prompts.
- Generated evaluation reports are reproducible and must not be edited by hand.

## Reproduce the portfolio checks

From the repository root:

```bash
uv sync --locked --all-groups
uv run python -m scripts.run_evaluation \
  --output evaluation/reports/phase18-reference.json
uv run python -m scripts.validate_portfolio
```

The first command uses the locked dependency graph. The evaluation command uses
`evaluation/expected_outputs/phase11_reference_results.json` and
`evaluation/release_thresholds.json`. The portfolio validator checks required
files, local Markdown links, commands, referenced result metadata, and common
secret patterns.
