# Architecture Principles

## Purpose

These principles guide design, implementation, review, and release decisions for Industrial AI Operations Copilot. When a local optimization conflicts with a principle, the principle takes precedence unless an Architecture Decision Record documents an approved exception.

## AP-01 — Grounded by design

Document-based claims must be traceable to retrieved, approved evidence. Sensor observations must be traceable to timestamped readings.

Implications:

- citations are structured data, not model-generated decoration
- retrieved chunks retain document identity, revision, and section
- unsupported claims are removed or explicitly labelled as hypotheses
- historical incidents inform likelihood but do not prove the current root cause

## AP-02 — Human-in-the-loop

The system may propose an action but must not execute a write operation without explicit human approval.

Implications:

- read and write capabilities are separated
- proposed actions have a reviewable payload and lifecycle
- approval is bound to a specific payload version
- rejection, expiry, and replay are explicitly handled

## AP-03 — Safety first

Industrial safety constraints take priority over task completion and convenience.

Implications:

- applicable safety procedures are retrieved before physical inspection advice
- instructions to bypass safety procedures are refused
- low confidence or missing evidence produces a safe uncertainty response
- critical safety regression tests block release

## AP-04 — Observable by default

The behavior of the agent must be inspectable without exposing hidden chain-of-thought.

Implications:

- every request receives a correlation ID
- graph nodes, tools, retrieval, models, retries, and approval events are traced
- the UI may show a bounded decision log, such as tools used and evidence found
- secrets and hidden reasoning are excluded from logs and traces

## AP-05 — Evaluation-driven development

New behavior is accepted based on measurable outcomes, not only manual impressions.

Implications:

- evaluation cases are added as components are built
- confirmed failures become regression cases
- critical safety gates are deterministic where possible
- prompt, tool, model, index, and dataset versions are recorded

## AP-06 — Explicit contracts at boundaries

API requests, agent state, tool arguments, tool results, database records, and model outputs use typed, validated contracts.

Implications:

- malformed data is rejected at the earliest boundary
- units and timestamps are explicit
- domain models are not replaced by unstructured dictionaries
- provider-specific response formats are normalized before entering the domain layer

## AP-07 — Least privilege and bounded tools

The agent receives narrow capabilities rather than general infrastructure access.

Implications:

- no unrestricted SQL tool
- explicit query limits and time windows
- timeouts and retry limits
- managed identity and minimal roles in Azure
- separate permissions for reading, proposing, approving, and executing

## AP-08 — Fail safely

Dependency failure or incomplete evidence must never be disguised as a successful diagnosis.

Implications:

- dependency failures have documented fallback behavior
- retries are bounded
- tool loops are detected
- cache failure falls back to the authoritative source
- observability failure does not invent data or silently approve actions

## AP-09 — Current approved information wins

The current approved document revision is the default source of truth.

Implications:

- document status and revision are indexed metadata
- superseded documents are excluded from normal retrieval
- conflicts are surfaced rather than silently merged
- citations include the revision used

## AP-10 — Provider integrations remain replaceable

Azure services are intentional deployment choices, but core domain and safety behavior should not depend on provider-specific response objects.

Implications:

- retrieval, model, tracing, and persistence integrations are isolated behind interfaces
- local deterministic substitutes are available for tests
- domain logic remains testable without network access

## AP-11 — Reproducibility over hidden state

Data generation, migrations, evaluation, and deployment must be repeatable.

Implications:

- synthetic data uses a fixed seed
- database changes use migrations
- infrastructure is defined as code
- releases identify commit, image, prompt, model, index, and evaluation versions

## AP-12 — MVP discipline

Features are included when they improve the core diagnostic workflow and can be evaluated.

Implications:

- one equipment type in the MVP
- no multi-agent architecture
- no live equipment control
- no SAP or streaming IoT integration
- Redis, voice, vision, and predictive maintenance remain optional until the core quality gates pass
