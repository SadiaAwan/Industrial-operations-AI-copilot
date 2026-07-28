# Future Work

## Purpose

These capabilities are intentionally excluded from the MVP. They should be reconsidered only after the single-agent centrifugal-pump workflow satisfies its safety, retrieval, tool, approval, and operational quality gates.

## Near-term extensions

### Retrieval caching

Introduce Redis-backed caching for embeddings or retrieval results after defining:

- cache keys
- document-version awareness
- invalidation behavior
- privacy and retention
- fallback when Redis is unavailable

Cached agent responses should not be introduced for safety-sensitive diagnostics until freshness and session-context risks are evaluated.

### Stronger authentication and authorization

- organization identity provider
- technician, approver, maintainer, and evaluator roles
- separation of duties for approval
- audit review and access retention

### Private Azure networking

- private endpoints
- virtual network integration
- restricted ingress
- controlled administrative access

### Advanced release strategies

- canary revision
- automated post-deployment evaluation
- progressive traffic shifting
- automated rollback thresholds

## Data and industrial integration

### Streaming sensor ingestion

Add real-time ingestion only after defining event ordering, late data, unit validation, backpressure, retention, and safe handling of stale readings.

Potential services:

- Azure IoT Hub
- Event Hubs
- stream-processing layer

### SAP or CMMS integration

Integrate with a maintenance platform through a narrowly scoped adapter. Preserve payload-bound approval, idempotency, audit, and least privilege.

### Additional equipment types

Add compressors, motors, or heat exchangers through separate domain datasets and evaluation suites. Do not reuse pump-specific prompts or thresholds without validation.

### Predictive maintenance model

Introduce a dedicated time-series or anomaly model whose output is treated as another evidence source, not as ground truth. Track training data, model version, drift, and calibration separately from the language model.

## Agent capabilities

### Model Context Protocol integration

Evaluate MCP for governed access to enterprise tools. MCP does not replace application authorization, input validation, approval, or tracing.

### Multi-agent architecture

Consider specialized agents only if evaluation demonstrates that one controlled graph cannot meet clear requirements. Define coordination limits, shared-state policy, failure propagation, and added cost before adoption.

### Voice interface

Add speech input and output for hands-busy workflows after addressing noisy environments, confirmation of safety-critical content, identity, and accessibility.

### Image understanding

Support equipment labels, gauge images, or visible damage only with image-specific evaluation, privacy controls, and explicit uncertainty. Image analysis must not replace physical safety procedures.

## Continuous improvement

Future versions should continue the loop:

```text
Production requests
→ traces and feedback
→ curated evaluation cases
→ regression testing
→ prompt, retrieval, or tool improvement
→ gated deployment
```

No future capability is considered complete without:

- explicit requirements
- an architecture decision when material
- automated tests
- observability
- evaluation criteria
- failure behavior
- security and safety review
