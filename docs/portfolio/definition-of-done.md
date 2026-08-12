# Final Definition of Done

This checklist distinguishes repository-complete evidence from environment
acceptance. Checked items are reproducible from the repository. Deployment items
remain unchecked until retained artifacts for the exact release are reviewed.

## Repository delivery

- [x] README explains purpose, safety boundary, architecture, quick start, tests,
  evaluation, Azure delivery, scope, and evidence links.
- [x] Architecture and request/approval diagrams render as Mermaid on GitHub.
- [x] Local demo uses synthetic data and requires no Azure credentials.
- [x] Screenshot policy excludes secrets, personal data, cloud identifiers, and
  hidden prompts.
- [x] Evaluation report records dataset ID, version, SHA-256, thresholds, cases,
  metrics, and a reproducible timestamp.
- [x] Latency and cost graph cites the deterministic fixture and carries a
  non-production disclaimer.
- [x] Limitations, lessons learned, roadmap, and Azure evidence boundaries are explicit.
- [x] Local Markdown links and required commands pass the portfolio validator.
- [x] Quality, tests, and release evaluation pass from the locked environment.
- [x] No committed portfolio asset contains a detected credential pattern.

## New-developer verification

Run from a fresh clone:

```bash
uv sync --locked --all-groups
uv run python -m scripts.run_evaluation \
  --generated-at 2026-08-12T00:00:00+00:00 \
  --output evaluation/reports/phase18-reference.json
git diff --exit-code -- evaluation/reports/phase18-reference.json
uv run python -m scripts.validate_portfolio
```

For the product walkthrough:

```bash
cp .env.example .env
docker compose up --build --wait
docker compose ps
docker compose down
```

PowerShell users replace `cp` with `Copy-Item`.

## Environment acceptance still required

- [ ] Azure what-if reviewed for the release commit.
- [ ] Immutable API and UI image digests retained with SBOM and scan results.
- [ ] Staging deployment and smoke checks accepted.
- [ ] Representative latency, cost, capacity, and quota evidence reviewed.
- [ ] Application rollback, database restore, and search reindex rehearsed.
- [ ] Accessibility and operator walkthrough accepted.
- [ ] Monitoring, alerts, incident roles, and escalation contacts verified.
- [ ] Production promotion approved with no safety-critical exception.

The repository is portfolio-delivery complete when its automated checks pass.
Production readiness is a separate decision and cannot be inferred from checked
repository items alone.
