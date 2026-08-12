# Application rollback runbook

Rollback restores previously accepted API and UI image digests. It does not
automatically reverse database migrations or data mutations.

## Preconditions

- Incident commander or release owner approved rollback.
- Previous `deployment-<environment>-<commit>` and release-manifest artifacts exist.
- The selected release passed staging acceptance.
- Database changes since that release are backward compatible, or a separate
  database recovery plan is approved.

## Procedure

1. Record the current and target commit, API digest, UI digest, reason, and approver.
2. Run the environment promotion workflow in `what-if` mode with the target
   `verified_commit` and original `publish_run_id`.
3. Review the plan for image-only changes. Stop if it replaces or deletes stateful
   resources, expands RBAC, or changes networking.
4. Run the same workflow in `deploy` mode and approve the protected environment.
5. Verify `/health`, `/ready`, Streamlit health, a read-only diagnostic, citations,
   approval enforcement, logs, traces, and error rate.
6. Upload or link the resulting deployment evidence in the incident record.

## Abort conditions

Stop and escalate when the release manifest is missing, a digest differs from the
accepted artifact, the what-if contains stateful changes, migration compatibility
is unknown, or post-deployment readiness is not `ready`.

## Return to the current release

Treat reapplication as another promotion: use the original current release
manifest, repeat what-if and protected approval, and capture new evidence. Never
move mutable tags or rebuild an old commit to simulate rollback.
