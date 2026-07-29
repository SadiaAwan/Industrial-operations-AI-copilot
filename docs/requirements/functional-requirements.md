# Functional Requirements

## Purpose

Industrial AI Operations Copilot is a decision-support system for technicians troubleshooting centrifugal pumps. It combines approved technical documentation, simulated sensor readings, maintenance history, and historical incidents. It does not control equipment or make autonomous maintenance decisions.

## Actors

- **Technician** — investigates a machine condition and reviews recommendations.
- **Approver** — approves or rejects a proposed write action.
- **Maintainer** — manages documents, test data, prompts, and system configuration.
- **Evaluator** — reviews traces, feedback, and evaluation results.

## Diagnostic workflow

### FR-001 — Submit a diagnostic request

The technician shall be able to submit a natural-language question about a centrifugal pump.

Acceptance criteria:

- The request accepts a message and an optional session identifier.
- The request is rejected with a validation error when the message is empty.
- The system assigns a traceable request identifier.

### FR-002 — Identify the machine

The system shall identify the target machine from the request or active session.

Acceptance criteria:

- A valid machine ID is included in the structured result.
- The system asks for clarification when no machine can be identified.
- The system reports that the machine was not found when the ID is unknown.
- Diagnostic tools are not called until a valid machine has been identified.

### FR-003 — Classify user intent

The system shall distinguish between diagnostic, sensor, maintenance, incident, safety, and work-order-draft requests.

Acceptance criteria:

- The classified intent is available to the agent workflow.
- Only tools relevant to the intent are selected.
- Unsupported requests receive a bounded explanation rather than an invented result.

### FR-004 — Retrieve technical documentation

The system shall search approved manuals, procedures, and safety instructions.

Acceptance criteria:

- Search supports both semantic similarity and exact terms such as machine IDs and fault codes.
- Results can be filtered by machine type, document type, status, and revision.
- Superseded or unapproved documents are excluded from normal answers.
- An unavailable search service produces a controlled failure response.

### FR-005 — Read sensor data

The system shall retrieve recent simulated sensor readings for a known machine.

Acceptance criteria:

- The caller can specify a bounded time window.
- Returned readings contain timestamps, values, and units.
- Missing, stale, or invalid readings are explicitly marked.
- The tool cannot query an unbounded time range.

### FR-006 — Read maintenance history

The system shall retrieve a bounded list of maintenance records for a known machine.

Acceptance criteria:

- Records are returned in descending chronological order.
- Each record includes its date, maintenance type, summary, and affected component when known.
- Empty history is reported as missing evidence, not as proof that no maintenance occurred.

### FR-007 — Find similar incidents

The system shall find historical incidents relevant to the machine and observed symptoms.

Acceptance criteria:

- Results include incident ID, symptoms, root cause, action taken, and similarity evidence.
- The number of results is bounded.
- Historical root causes are presented as supporting evidence, not as a diagnosis of the current case.

### FR-008 — Assess available evidence

The system shall assess whether the available documents, sensor readings, maintenance records, and incidents are sufficient for a recommendation.

Acceptance criteria:

- Missing and conflicting evidence is explicitly identified.
- Confidence is represented using a defined, bounded scale.
- The system does not present a certain diagnosis when the evidence is insufficient.

### FR-009 — Produce a structured recommendation

The system shall return a recommendation with distinct sections for:

- current condition
- relevant evidence
- possible causes
- recommended checks
- safety notice
- sources
- proposed action, when applicable

Acceptance criteria:

- Observed facts are separated from hypotheses.
- Possible causes are ranked and qualified by confidence.
- Recommended checks use a safe troubleshooting order.
- The response states that it is decision support rather than an automatic control action.

### FR-010 — Provide verifiable citations

Every document-based claim shall include a citation that resolves to retrieved evidence.

Acceptance criteria:

- A citation includes document ID, title, revision, and section.
- The citation points to a chunk actually returned during the request.
- The system does not generate a citation when no supporting source exists.
- Conflicting revisions are disclosed and the current approved revision is preferred.

## Safety and action workflow

### FR-011 — Enforce safety procedures

The system shall refuse instructions that require bypassing an applicable safety procedure.

Acceptance criteria:

- Requests to inspect operating equipment contrary to lockout/tagout guidance are refused.
- The response provides a safe alternative grounded in the approved procedure when available.
- Safety validation is recorded in the request trace.

### FR-012 — Create a work-order draft

The system shall be able to create a proposed work-order payload.

Acceptance criteria:

- The result is explicitly labelled as a draft.
- Creating the draft does not execute a write action against an external maintenance system.
- The draft contains the machine, priority, summary, supporting evidence, and approval requirement.

### FR-013 — Require human approval for write actions

No write action shall execute without explicit human approval.

Acceptance criteria:

- A proposed action is stored with a `pending` status.
- The reviewer can inspect the exact payload before deciding.
- Approval is bound to the action, payload version, reviewer, and timestamp.
- A modified or expired proposal requires new approval.
- Rejected proposals cannot execute.
- Approval and rejection events are auditable.

## Session and user experience

### FR-014 — Maintain bounded session state

The system shall retain operational context within a diagnostic session.

Acceptance criteria:

- The active machine, previous tool results, retrieved sources, and pending action can be reused.
- Session state is not treated as a new authoritative source.
- Hidden chain-of-thought is neither stored nor displayed.
- A new session does not inherit another session's state.

### FR-015 — Stream a response

The API shall support both regular and streamed diagnostic responses.

Acceptance criteria:

- A client can cancel a stream.
- Cancellation does not leave a write action approved or executed.
- The final streamed payload conforms to the same response schema as a regular response.

### FR-016 — Display decision-support information

The user interface shall display:

- machine status and relevant sensor trends
- the structured recommendation
- citations
- tools used
- risk level and confidence
- latency, token usage, and estimated cost
- pending action and approval controls

The interface shall not display hidden chain-of-thought.

### FR-017 — Collect feedback

The technician shall be able to mark a response as helpful or not helpful and optionally provide a comment.

Acceptance criteria:

- Feedback is linked to the request, session, agent version, and prompt version.
- Feedback submission does not modify the original trace.
- Feedback can be used to curate later evaluation cases.

## Operations and administration

### FR-018 — Trace each request

The system shall trace the end-to-end request and its component operations.

Acceptance criteria:

- Agent nodes, model calls, retrieval calls, tool calls, retries, failures, and approval events are correlated.
- Token usage, estimated cost, and latency are recorded when available.
- Secrets and credentials are excluded from traces.

### FR-019 — Support health and readiness checks

The API shall expose separate health and readiness endpoints.

Acceptance criteria:

- Liveness reports whether the application process is running.
- Readiness reflects required dependency availability.
- Dependency details do not expose credentials or sensitive configuration.

### FR-020 — Support reproducible evaluation

The system shall run versioned evaluation datasets against retrieval, tools, safety controls, and end-to-end behavior.

Acceptance criteria:

- Evaluation results identify dataset, application, model, and prompt versions.
- Critical regressions can fail CI.
- A confirmed production failure can be added as a regression case.

## Out of scope for the MVP

- controlling or changing real industrial equipment
- autonomous maintenance decisions
- creating a real external work order
- supporting equipment types other than centrifugal pumps
- production SAP integration
- production IoT Hub or streaming sensor ingestion
- predictive-maintenance model training
- multi-agent orchestration
- voice or image interaction
