# Roadmap

Roadmap items are ordered by risk reduction and evidence value, not novelty.

## Next: validate the delivered system

- deploy the exact immutable release to Azure staging;
- retain what-if, deployment, SBOM, scan, evaluation, and telemetry evidence;
- measure p50/p95/p99 latency and real provider cost under a documented workload;
- complete operator, accessibility, incident, rollback, restore, and reindex reviews;
- resolve every Phase 17 exception with owner, severity, mitigation, and expiry.

Exit criterion: one commit and image manifest has accepted staging evidence with
no unresolved safety-critical exception.

## Then: strengthen production controls

- organization authentication and technician/approver/evaluator roles;
- separation of duties and audit-retention policy;
- private endpoints, restricted ingress, and approved administrative access;
- capacity, quota, budget, alert ownership, SLO, RTO, and RPO definitions;
- progressive Container Apps traffic and automated rollback signals.

Exit criterion: threat model, operational objectives, access review, and recovery
evidence are approved for the intended environment.

## Expand evidence before capability

- collect reviewed feedback and curate privacy-safe regression cases;
- add multilingual, ambiguity, stale-data, outage, and adversarial cases;
- evaluate additional pump conditions and document revisions;
- measure prompt, retrieval, and model changes against the same baseline;
- add calibration and operator-usefulness studies.

Exit criterion: new behavior passes critical gates and does not regress the
accepted baseline beyond the declared tolerance.

## Future integrations

- governed streaming sensor ingestion with ordering and freshness policy;
- narrow CMMS adapter preserving idempotency and payload-bound approval;
- additional equipment types with separate schemas, prompts, and evaluations;
- anomaly or predictive models treated as versioned evidence sources;
- image or voice input only after modality-specific privacy and safety testing.

Multi-agent orchestration is not a default goal. It should be introduced only if
a controlled single graph cannot meet a measured requirement and the additional
coordination, latency, cost, and failure modes are justified.

The broader backlog remains in [future work](../roadmap/future-work.md).
