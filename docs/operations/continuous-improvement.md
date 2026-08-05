# Continuous improvement and prompt lifecycle

This process turns reviewed operational feedback into reproducible evaluation
cases. Feedback never changes a production prompt automatically.

## Traceability contract

Every stored feedback record identifies:

- `session_id` and `request_id` for the user workflow;
- `trace_id` for the corresponding MLflow trace;
- `agent_version` and `model_version`;
- `prompt_version` and the prompt file's `prompt_sha256` digest.

The digest distinguishes an exact prompt artifact from a reused or incorrectly
edited version label. Prompt files are registered in
`app/agent/prompts/manifest.json`. Loading fails if a file no longer matches its
registered digest.

## Privacy and review

Feedback comments are optional and limited to 500 characters. Email addresses,
phone numbers, bearer credentials, passwords, tokens, secrets, and API keys are
redacted before the application service receives the feedback. Operators must
still avoid entering personal data or credentials.

Raw comments and session IDs are not copied into evaluation datasets. Only a
human-reviewed negative-feedback record may be selected. The curated artifact
retains feedback and trace identifiers for an authorized evaluator to audit the
source.

Access to raw feedback and traces must be role-restricted. Production retention
periods must be configured according to the organization's privacy policy.

## Feedback-to-evaluation workflow

1. An evaluator locates negative feedback by trace or session.
2. The evaluator inspects the trace, citations, tool calls, prompt digest, and
   applicable document revisions.
3. The evaluator writes explicit expected outcomes and marks the record as
   `reviewed` and `include_in_evaluation`.
4. Export only the fields accepted by `FeedbackCaseInput`; do not export raw
   comments, user identity, or session transcripts.
5. Generate a versioned artifact:

   ```bash
   uv run python -m scripts.curate_feedback_eval_cases \
     --input evaluation/reviewed_feedback.json \
     --output evaluation/datasets/feedback_regressions_v1.json \
     --dataset-id feedback-regressions \
     --dataset-version 1.0.0
   ```

6. Review the generated source fingerprint and commit the dataset separately.
7. Implement a candidate prompt under a new version. Never modify the content
   behind an existing digest.
8. Run the candidate and baseline against the same dataset and environment.
9. Call `evaluate_prompt_candidate`; promotion is blocked if a critical gate,
   aggregate quality gate, or baseline regression check fails.
10. After review, mark the candidate active and the old version retired in a
    separate PR. Retain the old artifact for rollback and trace interpretation.

## Prompt comparison and release evidence

Each prompt-change PR must record:

- baseline and candidate prompt versions and SHA-256 digests;
- application, agent, model, dataset, and document-index versions;
- evaluation report and dataset fingerprint;
- metric deltas, gate result, reviewer, and rollback version.

The candidate must pass safety, approval, groundedness, citation, tool behavior,
task completion, latency, and cost gates. A passing average never overrides a
critical safety or unauthorized-write failure.

## Controlled failures and rollback

Invalid manifests, digest mismatches, unreviewed feedback, duplicated case IDs,
and failed evaluation gates stop the workflow. They do not update the active
prompt. If production monitoring detects regression after release, restore the
previous registered prompt version and open a new reviewed feedback case; do not
silently edit the active file.
