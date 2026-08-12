# Phase 17 completion checklist

Phase 17 is complete only when every item is linked to retained evidence for the
same verified commit and immutable API/UI digests.

## Automated staging checks

- [ ] Development accepted the release-manifest digests.
- [ ] Staging promotion completed through its protected GitHub environment.
- [ ] API liveness and dependency readiness passed.
- [ ] Streamlit health passed.
- [ ] Database schema is at all Alembic heads and deterministic seed completed.
- [ ] Approved documents were reindexed and retrieval checks passed.
- [ ] End-to-end evaluation gates passed in the deployed image.
- [ ] Application Insights and Log Analytics resources were found.
- [ ] Runtime least-privilege audit found no broad resource-group assignments.

## Human readiness review

- [ ] Operator walkthrough covered normal and degraded diagnostic paths.
- [ ] Keyboard, focus, labels, contrast, zoom, and error announcements were reviewed.
- [ ] Exact approval payload, rejection, expiry, and replay behavior were demonstrated.
- [ ] Incident roles and escalation contacts are assigned.
- [ ] Application rollback was rehearsed using prior immutable digests.
- [ ] Database restore was rehearsed on an isolated recovery server.
- [ ] Search reindex procedure was rehearsed without removing known-good content.
- [ ] Cost forecast, service quotas, capacity headroom, and alert owners were approved.
- [ ] Exceptions have an owner, mitigation, severity, and expiry date.

## Evidence and decision

- [ ] Deployment, what-if, release manifest, SBOM, scan, evaluation, and staging
  acceptance artifacts are retained.
- [ ] The `staging-acceptance-<commit>` artifact validates successfully.
- [ ] Production workflow accepts the same commit and staging acceptance run ID.
- [ ] Release owner records `accepted`, `accepted with expiring exceptions`, or
  `rejected`; safety-critical exceptions always mean `rejected`.

Do not mark the phase complete based only on template compilation or a successful
deployment. Operational recovery and operator acceptance must also be evidenced.
