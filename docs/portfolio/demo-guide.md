# Reproducible demo guide

This walkthrough uses only the repository's synthetic pump records and mock
runtime. It demonstrates delivery and safety contracts without presenting mock
output as a live model or Azure result.

## 1. Prepare the environment

Prerequisites are Git and Docker Compose v2. From the repository root:

```bash
cp .env.example .env
docker compose up --build --wait
docker compose ps
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
docker compose up --build --wait
docker compose ps
```

Expected services are `postgres`, completed `database-init`, healthy `api`, and
healthy `ui`. Confirm the public endpoints:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
```

Open <http://localhost:8501> and <http://localhost:8000/docs>.

## 2. Demonstrate the product boundary

1. Select synthetic machine `P-104` in Streamlit.
2. Ask: `What is the current condition and what should a technician check?`
3. Confirm that the response identifies local mock mode and does not claim a
   live diagnosis or paid model execution.
4. Inspect the machine-status and session API operations in FastAPI docs.
5. Confirm that correlation IDs are returned and that malformed identifiers
   produce structured errors.

Talking point: local mode validates API, UI, database, session, feedback, and
delivery contracts. Deterministic agent and guardrail behavior is exercised by
the automated evaluation suite.

## 3. Demonstrate safety and approval

Use the automated gates to avoid implying that the mock UI performs a real
maintenance-system write:

```bash
uv run pytest tests/evaluation/test_phase07_gates.py -q
uv run pytest tests/unit/test_approval_workflow.py -q
```

Show that:

- unsafe action and unauthorized write rates are zero in the gate suite;
- a work-order capability creates a draft only;
- approval is bound to the exact payload and expires;
- a changed payload or replay requires a new approval;
- no equipment-control tool exists.

## 4. Reproduce evaluation evidence

```bash
uv run python -m scripts.run_evaluation \
  --output evaluation/reports/phase18-reference.json
```

Expected terminal result:

```text
EVALUATION PASSED: industrial-copilot-reference@1.0.0 (3 cases)
```

Compare the generated report with the committed reference evidence:

```bash
git diff --exit-code -- evaluation/reports/phase18-reference.json
```

The [results page](results-and-lessons.md) explains the metrics and why fixture
latency and cost must not be presented as production benchmarks.

## 5. Explain Azure delivery without overstating deployment

Open the [architecture diagram](architecture.md) and
[Azure deployment runbook](../operations/azure-deployment.md). Demonstrate that:

- environment parameter files contain no secrets;
- GitHub Actions authenticates through OIDC;
- images are promoted by digest rather than rebuilt;
- staging acceptance precedes protected production promotion;
- rollback selects a previously verified revision and manifest.

If no retained what-if and deployment artifacts exist for the exact commit, say
that Azure is deployment-ready by code and workflow—not that it is currently
deployed.

## Screenshot capture policy

Screenshots are deliberately not committed as static proof because UI images
become stale and can accidentally expose workstation or cloud identifiers. For a
portfolio presentation, capture fresh images from the synthetic local demo:

1. use an incognito browser with bookmarks and profile controls hidden;
2. show only `localhost`, synthetic machine IDs, and generated request IDs;
3. crop out the desktop, terminal environment, browser profile, and notifications;
4. inspect the image for tokens, email addresses, tenant/subscription IDs,
   connection strings, personal feedback, and hidden prompt text;
5. store approved images outside Git, or add them only after a reviewer signs off
   using the checklist below.

| Capture | Required content | Forbidden content |
| --- | --- | --- |
| Overview | synthetic machine selector and advisory boundary | browser identity or unrelated tabs |
| Recommendation | structured result, uncertainty, citations, safety notice | hidden reasoning or real operational data |
| Approval | exact synthetic payload and pending state | credentials or real work-order identifiers |
| Observability | aggregate safe metrics and correlation ID | request payload, prompt, token, tenant ID |

## Cleanup

```bash
docker compose down
```

Use `docker compose down --volumes` only when the local synthetic PostgreSQL
volume may be deleted.
