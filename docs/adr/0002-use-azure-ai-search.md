# ADR-0002: Use Azure AI Search for document retrieval

- Status: Accepted
- Date: 2026-07-28

## Context

Technical troubleshooting requires both exact matching of machine identifiers, fault codes, and procedure terms, and semantic matching of symptoms. Retrieval must filter by machine type, document type, approval status, and revision and must return metadata suitable for verifiable citations.

## Decision

Use Azure AI Search as the deployed document index. Implement hybrid retrieval using keyword and vector search, with metadata filters and rank fusion. Retain source documents outside the index and treat the index as a derived retrieval artifact.

## Alternatives

### PostgreSQL with pgvector

Would reduce the number of services and work well for a smaller corpus, but requires more application-owned search tuning and provides a less direct demonstration of the selected Azure search stack.

### Dedicated vector database

Provides vector-search capabilities but adds another platform and does not inherently solve exact keyword matching, revision filters, or source-document governance.

### Vector-only retrieval

Is simple but performs poorly for exact identifiers and does not meet the hybrid retrieval requirement.

### Local in-memory retrieval

Useful as a deterministic test adapter, but not the deployed production-like search service.

## Consequences

### Positive

- keyword and semantic retrieval can be combined
- metadata filtering supports document governance
- Azure deployment and operational experience are demonstrated
- retrieval can be evaluated independently of the agent

### Negative

- local development requires an adapter or mock
- index schema and document versions must be managed
- service cost, quota, and regional availability must be considered

### Constraints

- superseded and unapproved documents are excluded from normal results
- every returned chunk keeps source, revision, and section metadata
- provider response objects are normalized behind the retrieval interface
- retrieval quality gates must pass before agent integration
