# Limitations

## Product scope

- The domain covers centrifugal pumps, not arbitrary industrial equipment.
- Sensor, incident, maintenance, and work-order data is synthetic.
- Local mock mode demonstrates delivery contracts but performs no live diagnosis.
- Work orders remain reviewable drafts; no production CMMS write integration exists.
- The copilot never controls equipment and cannot replace site procedures or a
  qualified technician's judgment.

## Evaluation scope

- The committed portfolio report contains three deterministic reference cases.
- Fixture latency and estimated cost validate scorer behavior; they do not measure
  network, model-provider, database, or Azure runtime performance.
- The suite is a regression gate, not proof of universal correctness, calibration,
  availability, accessibility, or operator usefulness.
- New equipment, languages, tools, prompts, models, and document revisions require
  representative cases and threshold review.

## Data and retrieval

- No real-time sensor ingestion, event ordering, drift detection, or stale-data
  policy is implemented.
- Retrieval quality depends on approved document ingestion and metadata accuracy.
- Search fallback must not be interpreted as permission to make uncited claims.
- Synthetic documents and incidents cannot represent every site-specific hazard.

## Security and identity

- Production end-user authentication and role mapping remain deployment-specific.
- Infrastructure defines managed identity and least privilege, but runtime access
  requires an Azure review and post-deployment audit.
- Public endpoint posture may need private endpoints, restricted ingress, and
  organization-specific network controls.

## Operations and Azure

- A successful local demo or Bicep compilation does not prove a live deployment.
- Availability, recovery objectives, capacity, quota, regional resilience, and
  cost require environment measurements and owner approval.
- Database restore, search reindex, rollback, accessibility, and operator
  acceptance remain incomplete until retained Phase 17 evidence is attached.
- Screenshots are not treated as operational proof and are excluded until they
  pass the synthetic-data and privacy review in the demo guide.

## Model behavior

- Language-model output remains probabilistic and untrusted.
- Citation and safety gates reduce known risks but cannot guarantee that every
  harmful ambiguity or missing source is detected.
- Hidden chain-of-thought is neither required nor stored; concise evidence and
  decision metadata are used instead.
