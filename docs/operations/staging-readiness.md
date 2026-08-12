# Staging and operational readiness

Phase 17 acceptance proves that a verified release can be deployed, operated, and
restored without undocumented steps. A passing workflow is evidence, not a waiver
for human review.

## Required sequence

1. Publish images after successful `main` CI and retain the release manifest.
2. Promote the same digests to development and complete smoke checks.
3. Promote them to staging using the protected staging environment.
4. Run `Phase 17 staging acceptance` with deployment run ID and verified commit.
5. Complete operator/accessibility review and rollback rehearsal.
6. Review the resulting `staging-acceptance-<commit>` artifact.

## Operator and accessibility acceptance

The reviewer verifies keyboard navigation, visible focus, readable labels, error
announcements, contrast, and usable layout at common zoom levels. The functional
walkthrough must distinguish observed conditions, evidence, hypotheses, actions,
uncertainty, citations, and safety notices. The approval view must show the exact
payload and must not imply that UI approval bypasses backend enforcement.

Test normal, degraded, timeout, unavailable, unsafe-input, missing-citation,
approval, rejection, and replay scenarios. Record findings and block acceptance
for any safety-critical or task-blocking accessibility issue.

## Least-privilege review

Export role assignments for the staging resource group. Confirm that UI has only
ACR pull, API has only documented data-plane roles, PostgreSQL administration uses
the dedicated Entra group, and deployment identity scope is limited to declared
resources and role assignments. Every exception needs an owner and expiration.

## Cost and capacity review

Record current SKU, min/max replicas, Search replicas/partitions, PostgreSQL tier,
log retention, observed request rate, p95 latency, daily estimated model cost, and
Azure cost forecast. Compare observed headroom with expected demonstration load.

Production sizing is approved only when service quotas, regional availability,
monthly budget, scale limits, and alert thresholds have named owners. Do not raise
capacity speculatively without an observed or forecast requirement.

## Acceptance artifact

The workflow requires successful health/readiness, migrations, deterministic seed,
approved-document indexing, evaluation gates, monitoring resource checks,
least-privilege audit, rollback rehearsal, and operator acceptance. The artifact
binds those checks to the exact commit and API/UI digests.
