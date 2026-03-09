# Evidence & Audit

## Good-Faith Binder
- Generated per case as PDF + JSON manifest.
- Contents: comms timeline (email/SMS/mail/chat), delivery proofs, rules fired + citations, title chain summary, appraisal stats, offer versions, approvals, e-sign certificates.
- Each section references Cloud Storage object IDs + SHA-256 hashes recorded in `Document` table.

## Logging Requirements
- All inbound/outbound comms hashed (content hash + metadata) and stored immutably.
- SLA timers per communication ensure follow-ups; escalations recorded.
- RuleResult entries capture `citation`, `trigger_fields`, `input_snapshot` for reproducibility.

## Export Workflow
1. Attorney triggers export from workbench.
2. Backend queries Postgres + Cloud Storage; assembles binder with deterministic ordering.
3. Hash of final bundle stored + compared to per-section hash.
4. Audit event emitted with reason + persona + IP.

## Evidence Hooks
- Rules YAML includes `evidence_hooks` describing which fields to embed.
- Template renders automatically embed citations + doc IDs; binder aggregator cross-references them.
