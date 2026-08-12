# Azure AI Search reindex runbook

Use this procedure for initial staging load, approved document revisions, stale
index content, or index recovery. Only approved and effective manifest revisions
may be indexed.

## Preconditions

- Confirm target environment, search service, index name, and source commit.
- Review `data/documents_manifest.json` approval status, revision, and checksum.
- Capture the current index document count and active application image digests.
- Use managed identity or a short-lived bearer token; never pass API keys on CLI.

## Procedure

Run from the deployed API container so identity and network boundaries match the
application:

```bash
python -m scripts.index_documents --target azure
```

Then verify index count, representative hybrid queries, citations, document
revision filtering, and the retrieval evaluation suite. Record the manifest
commit, effective date, index name, document count, evaluation report, operator,
and UTC completion time.

## Failure and rollback

Stop on manifest validation, checksum, upload, or retrieval-gate failure. Do not
delete the previous known-good index until the replacement passes verification.
Prefer a versioned replacement index and reviewed alias/configuration switch when
the operation changes schema or embedding dimensions.
