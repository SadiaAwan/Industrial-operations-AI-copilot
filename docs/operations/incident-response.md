# Incident response runbook

Use this runbook when the API, UI, database, search, model, or telemetry path is
degraded. The copilot remains advisory throughout an incident; never bypass
approval controls or substitute it for approved plant safety procedures.

## Roles and severity

| Role | Responsibility |
|---|---|
| Incident commander | Owns severity, timeline, decisions, and closure |
| Operations lead | Assesses operator impact and safe fallback |
| Platform lead | Investigates Azure and deployment state |
| Application lead | Investigates API, agent, retrieval, and data behavior |

- SEV-1: unsafe recommendation exposure, approval bypass, or broad outage.
- SEV-2: material degradation without unsafe action execution.
- SEV-3: limited non-critical degradation with a documented workaround.

## First 15 minutes

1. Record UTC start time, reporter, environment, commit, and correlation IDs.
2. Stop promotion workflows and preserve deployment/evaluation artifacts.
3. Confirm `/health` and `/ready`; do not infer readiness from liveness.
4. Inspect Container Apps revision state, Application Insights failures, dependency
   latency, and PostgreSQL/Search availability.
5. If safety, citation, or approval integrity is uncertain, declare the copilot
   unavailable and direct operators to approved manuals and SOPs.
6. Decide whether to contain, roll back application images, or invoke a stateful
   recovery procedure. Record the decision and approver.

## Investigation commands

Authenticate with the incident-response identity and select the exact environment:

```bash
az containerapp revision list --resource-group <resource-group> --name <api-name>
az monitor app-insights query --app <app-insights-id> --analytics-query \
  "requests | where timestamp > ago(30m) | summarize count() by resultCode"
az postgres flexible-server show --resource-group <resource-group> --name <server>
az search service show --resource-group <resource-group> --name <search-service>
```

Never paste tokens, feedback comments, raw prompts, database rows, or secrets into
an incident ticket. Reference protected trace and artifact locations instead.

## Containment and recovery

- Application regression: use the rollback procedure and previously accepted
  release-manifest digests.
- Search corruption or stale revision: use the reindex procedure.
- Database schema/data issue: stop writes and use the database recovery procedure.
- Optional dependency outage: verify the documented degraded response and monitor
  circuit-breaker state; do not disable bounded retry policies.
- Suspected credential exposure: revoke the identity/session, preserve audit logs,
  rotate affected credentials, and review role assignments.

## Closure

Before closing, verify health, readiness, one safe diagnostic path, approval
enforcement, citations, telemetry, and evaluation gates. Attach the incident
timeline, root cause, exact recovery artifact, follow-up owners, and expiry dates.
Update this runbook when the response exposed an undocumented step.
