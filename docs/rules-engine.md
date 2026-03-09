# Rules Engine Specification

## Format
- Each jurisdiction lives in `rules/<state-code>.yaml` and follows semantic versioning (`version: 1.0.0`).
- Sections:
  - `metadata`: jurisdiction, citations, maintainers.
  - `triggers`: expressions evaluated against parcel/case data (value thresholds, dispute flags, timers, program type).
  - `deadlines`: relative offsets + statutory references.
  - `notices`: delivery methods, required recipients, document template IDs.
  - `offers`: minimum consideration, deposit/quick-take formulas.
  - `forums`: commissioners/jury guidance, arbitration requirements.
  - `evidence_hooks`: fields that must be persisted into the binder when the rule fires.

Example snippet:
```yaml
version: 1.0.0
state: TX
triggers:
  - id: valuation_threshold
    match: parcel.assessed_value > 250000 or case.dispute_level == 'HIGH'
    deadlines:
      - id: initial_offer
        offset_days: 30
        citation: "Tex. Prop. Code §21.0113"
    notices:
      - template_id: fol
        delivery: [certified_mail, portal]
        recipients:
          - owner_primary
          - lienholders
    evidence_hooks:
      - fields: [parcel.assessed_value, appraisal.summary, comms.last_contact_at]
        citation: "Tex. Prop. Code §21.0113(d)"
```

## Evaluation
- Implemented by `backend/app/services/rules_engine.py`.
- Loads YAML, validates against JSON schema, compiles trigger expressions using `asteval`-style safe evaluator.
- Output: `RuleResult` objects persisted with: rule_id, fired_at, citation, payload (fields + values), actor, version, evidence pointers.
- Deterministic: no LLM involvement; unit tests per jurisdiction live under `backend/tests/rules/`.

## Governance
- Alicia serves as Rules Steward; PRs require her review + legal sign-off.
- Quarterly review checklist: verify new statutes, confirm citations, re-run fixtures.
- Changelog auto-generated from rule metadata -> `docs/rules-changelog.md`.

## Evidence Hooks
- Every `RuleResult` is appended to the Good-Faith Binder; we store `payload` (JSONB), `citation`, `trigger_context`, and `hash`.
- Binders reference these entries plus the corresponding communication + template render.
