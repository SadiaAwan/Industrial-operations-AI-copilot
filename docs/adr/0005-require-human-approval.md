# ADR-0005: Require human approval for write actions

- Status: Accepted
- Date: 2026-07-28

## Context

The copilot is a decision-support system in a safety-sensitive domain. Model output is probabilistic and cannot be treated as authorization. Even a correct diagnostic recommendation does not grant permission to create or execute an operational action.

## Decision

Require explicit human approval before every write operation. Separate proposal creation, approval, and execution. Bind approval to the reviewer, action ID, exact payload version, and timestamp. The MVP creates work-order drafts and does not integrate with a real maintenance system.

## Alternatives

### Autonomous execution

Rejected because it conflicts with project purpose, safety posture, and portfolio realism.

### Prompt-only confirmation

Rejected because a textual instruction is not an enforceable authorization boundary.

### Approval for high-risk actions only

Rejected for the MVP because action-risk classification is not mature enough to waive approval safely.

### No write capability

Safer but would not demonstrate a realistic proposal and approval lifecycle.

## Consequences

### Positive

- authorization remains a human responsibility
- proposal and execution are auditable
- unsafe or changed payloads can be blocked
- the architecture can later integrate with an external system without granting the model direct access

### Negative

- workflow and persistence are more complex
- approval introduces latency and user interaction
- stale, duplicate, expired, and concurrent decisions need handling

### Constraints

- rejected or expired proposals cannot execute
- changing the payload invalidates prior approval
- replay and duplicate execution are prevented
- all approval events are traced
- no prompt or agent route may bypass the approval service
