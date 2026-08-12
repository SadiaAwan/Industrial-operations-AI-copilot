# Portfolio architecture

This view connects the local demo, application boundaries, Azure resources, and
delivery controls. Detailed component responsibilities remain in the
[system overview](../architecture/system-overview.md).

```mermaid
flowchart TB
    Reviewer[Technician or reviewer]

    subgraph Experience[Experience]
        UI[Streamlit UI]
        API[FastAPI API]
    end

    subgraph DecisionSupport[Controlled decision support]
        Graph[LangGraph workflow]
        Guardrails[Citation, safety, and uncertainty gates]
        Approval[Payload-bound human approval]
        ReadTools[Allow-listed read tools]
        DraftTool[Draft-only write tool]
    end

    subgraph Evidence[Versioned evidence]
        Search[Azure AI Search]
        Blob[Blob documents]
        Postgres[(PostgreSQL)]
        Model[Model provider]
    end

    subgraph Operations[Operational evidence]
        MLflow[MLflow-compatible traces and evals]
        Monitor[Application Insights and Log Analytics]
    end

    subgraph Delivery[Delivery controls]
        GitHub[GitHub Actions with OIDC]
        ACR[Azure Container Registry]
        Bicep[Bicep environment modules]
        ACA[Azure Container Apps]
    end

    Reviewer --> UI --> API --> Graph
    Graph --> ReadTools
    Graph --> Guardrails
    Graph --> DraftTool --> Approval
    ReadTools --> Search --> Blob
    ReadTools --> Postgres
    Graph --> Model
    API -. correlation ID .-> MLflow
    Graph -. safe spans .-> MLflow
    API -. metrics and logs .-> Monitor
    GitHub --> ACR --> ACA
    GitHub --> Bicep --> ACA
    ACA --> API
    ACA --> UI
```

## Request and approval sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit
    participant API as FastAPI
    participant Agent as LangGraph
    participant Tools as Bounded tools
    participant Gates as Safety and citation gates
    participant Approval as Approval store

    User->>UI: Ask about a synthetic pump
    UI->>API: Validated request + correlation ID
    API->>Agent: Typed diagnostic state
    Agent->>Tools: Bounded evidence requests
    Tools-->>Agent: Typed evidence + source references
    Agent->>Gates: Structured candidate
    Gates-->>Agent: Validated result or safe stop
    Agent-->>API: Recommendation + uncertainty + citations
    API-->>UI: Structured response
    opt Work-order proposal
        User->>UI: Request draft
        UI->>API: Draft request
        API->>Approval: Store pending payload hash
        Approval-->>UI: Exact payload for human review
        User->>API: Approve or reject unchanged payload
    end
```

## Trust and failure boundaries

1. User, document, and model content is untrusted until validated.
2. The agent has no generic SQL or arbitrary execution capability.
3. Read and write paths are separate; draft creation is not execution.
4. Approval binds actor, payload hash, expiry, and one-time state transition.
5. External calls have bounded timeout, attempts, backoff, and circuit state.
6. Cache and observability are optional; their failure cannot fabricate or
   suppress the core diagnostic result.
7. Database and required evidence dependencies affect readiness, while liveness
   remains a process-level signal.

## Deployment modes

| Mode | Runtime | Evidence claim |
| --- | --- | --- |
| Local | Docker Compose, mock adapters, synthetic PostgreSQL data | Reproducible product walkthrough without paid services |
| CI | PostgreSQL service, deterministic evaluation and static checks | Contract, quality, safety, and release-gate evidence |
| Azure | Bicep, Container Apps, managed identity, data and monitoring services | Declared deployment design; live status requires retained deployment artifacts |
