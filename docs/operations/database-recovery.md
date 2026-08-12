# PostgreSQL backup and recovery runbook

Database recovery is a stateful and potentially destructive operation. It requires
an incident/change record, named approver, confirmed recovery point, and a verified
backup. Do not run recovery commands from an application deployment workflow.

## Routine verification

For each environment, record backup retention, earliest restore point, latest
restore point, high-availability state, and the date of the last restore rehearsal:

```bash
az postgres flexible-server show --resource-group <resource-group> --name <server> \
  --query '{backup:backup,highAvailability:highAvailability,state:state}'
```

Production restore rehearsals must target an isolated recovery server. Never test
restore by overwriting the active server.

## Point-in-time restore rehearsal

1. Select a UTC restore point within the reported retention window.
2. Create an isolated recovery server using Azure point-in-time restore.
3. Restrict its network and identities to the recovery team.
4. Validate schema revision, row counts, approval audit records, feedback metadata,
   and representative read queries.
5. Record recovery point objective achieved, recovery duration, operator, and
   evidence links.
6. Delete the isolated recovery server only after evidence approval and according
   to the change record.

## Production recovery

Freeze application writes and preserve logs before mutation. Restore to a new
server, validate it, then switch application configuration through reviewed Bicep
and a protected deployment. Retain the former server until the recovery decision
and data reconciliation are approved.

Alembic downgrade is not a substitute for point-in-time recovery. Run a downgrade
only when the specific migration contains a reviewed, tested downgrade and the
incident plan explicitly authorizes it.
