# AI Orchestration

1. **Deterministic Rules**: Evaluate YAML rule packs (`rules/*`). No LLM involvement for statutory compliance.
2. **Evidence Assembly**: Capture triggered rule payloads + citations and stash them as draft `RuleResult` rows.
3. **Context Builder**: Gather parcel summary, appraisal stats, comms timeline, template metadata.
4. **LLM Assist (Optional)**: Call Vertex AI Gemini 1.5 Pro with instruction prompt limited to summarization / highlight detection. Output is non-binding and must reference citations.
5. **Attorney Gate**: Suggestions feed into counsel workbench; user must approve before binder export or filings.
6. **Feedback Loop**: `POST /ai/feedback` (future) logs attorney edits to adjust prompts + heuristics; no auto-learning without review.

Implementation reference: `app/services/ai_pipeline.py` and `/ai/drafts` endpoint.
