# AI-First Operations Runbook

> Operational procedures for LandRight AI-first modules.

## Table of Contents

1. [Adding a New State Pack](#adding-a-new-state-pack)
2. [Publishing State Pack Updates](#publishing-state-pack-updates)
3. [Handling Failed QA Checks](#handling-failed-qa-checks)
4. [Reviewing AI Decisions](#reviewing-ai-decisions)
5. [Processing Approval Requests](#processing-approval-requests)
6. [Running Regression Tests](#running-regression-tests)
7. [Investigating AI Failures](#investigating-ai-failures)
8. [Managing Citations and Sources](#managing-citations-and-sources)
9. [Cost Monitoring](#cost-monitoring)

---

## Adding a New State Pack

### Prerequisites
- State-specific legal research completed
- YAML file following `rules/schema/state_rules.schema.json`
- Counsel sign-off on requirements

### Steps

1. **Create the YAML file**
   ```bash
   # Copy template
   cp rules/tx.yaml rules/new_state.yaml
   
   # Edit with state-specific requirements
   vim rules/new_state.yaml
   ```

2. **Validate schema locally**
   ```bash
   cd backend
   python -c "
   from app.services.requirements_ops import RequirementsOpsService
   service = RequirementsOpsService()
   with open('../rules/new_state.yaml') as f:
       content = f.read()
   result = service.import_state_pack('XX', content)
   validation = service.validate_pack(result['pack']['id'])
   print('Valid:', validation.valid)
   print('Errors:', validation.errors)
   print('Warnings:', validation.warnings)
   "
   ```

3. **Run contract tests**
   ```bash
   pytest tests/test_requirements_ops.py -v
   ```

4. **Import via API**
   ```bash
   curl -X POST http://localhost:8050/rules/import_state_pack \
     -H "X-Persona: in_house_counsel" \
     -H "Content-Type: application/json" \
     -d '{"jurisdiction": "XX", "yaml_content": "..."}'
   ```

5. **Request validation**
   ```bash
   curl -X POST "http://localhost:8050/rules/validate_pack?pack_id=pack_xx_..." \
     -H "X-Persona: in_house_counsel"
   ```

6. **Publish after approval**
   ```bash
   curl -X POST http://localhost:8050/rules/publish \
     -H "X-Persona: in_house_counsel" \
     -H "Content-Type: application/json" \
     -d '{"pack_id": "pack_xx_..."}'
   ```

---

## Publishing State Pack Updates

### When to Update
- Legislative changes
- Court rulings affecting procedures
- Regulatory updates
- Error corrections

### Steps

1. **Create updated YAML**
   - Increment version number (semver)
   - Document changes in `change_summary`

2. **Import as new version**
   ```bash
   curl -X POST http://localhost:8050/rules/import_state_pack \
     -H "X-Persona: in_house_counsel" \
     -d '{"jurisdiction": "TX", "yaml_content": "..."}'
   ```

3. **Generate diff**
   ```bash
   curl "http://localhost:8050/rules/state/TX/diff?from=pack_old&to=pack_new" \
     -H "X-Persona: in_house_counsel"
   ```

4. **Review changes with counsel**
   - Verify deadline changes
   - Confirm citation accuracy
   - Check for unintended effects

5. **Run regression tests**
   ```bash
   python -c "
   from app.services.eval_harness import EvalHarness
   harness = EvalHarness()
   validation = harness.validate_state_pack('TX')
   print(validation)
   "
   ```

6. **Publish**
   - Previous version automatically archived
   - New version becomes active

---

## Handling Failed QA Checks

### Severity Levels

| Level | Action Required |
|-------|----------------|
| Red | Must fix before sending |
| Yellow | Review with counsel |
| Green | Informational only |

### Common Failures

**Missing Required Clause**
```
Error: Missing required clause: bill_of_rights_reference
Fix: Add language referencing Landowner Bill of Rights
```

Solution: Add the required language to the document template.

**Forbidden Language Detected**
```
Error: Cannot require waiver of all rights
Location: Position 1234
```

Solution: Rephrase or remove the flagged language.

**Name Inconsistency**
```
Error: Name 'John Doe' not found in document
```

Solution: Verify party name is correctly included in all required locations.

### Override Procedure

If proceeding despite warnings:

1. Document the reason in the approval notes
2. Get explicit counsel approval
3. Record override in audit trail:
   ```bash
   curl -X POST http://localhost:8050/qa/reports/{id}/override \
     -H "X-Persona: in_house_counsel" \
     -d '{"reason": "Justified override reason", "approved_by": "counsel-001"}'
   ```

---

## Reviewing AI Decisions

### When Review is Required
- Confidence below threshold
- Critical flags present
- Cross-verification disagreement

### Review Process

1. **Access the escalation queue**
   ```bash
   curl "http://localhost:8050/agents/escalations?status=open" \
     -H "X-Persona: in_house_counsel"
   ```

2. **Review decision details**
   ```bash
   curl http://localhost:8050/agents/escalations/{id} \
     -H "X-Persona: in_house_counsel"
   ```

3. **Check AI trace**
   ```bash
   curl http://localhost:8050/audit/ai-events/{event_id} \
     -H "X-Persona: in_house_counsel"
   ```

4. **Verify citations**
   ```bash
   curl http://localhost:8050/audit/citations/ai_decision/{decision_id} \
     -H "X-Persona: in_house_counsel"
   ```

5. **Resolve**
   - **Approve**: Accept as-is
   - **Modify**: Accept with changes
   - **Reject**: Reject decision, trigger re-analysis

   ```bash
   curl -X POST http://localhost:8050/agents/escalations/{id}/resolve \
     -H "X-Persona: in_house_counsel" \
     -d '{"outcome": "approved", "resolution": "Verified citations are accurate"}'
   ```

---

## Processing Approval Requests

### Approval Workflow

```
draft → qa_passed → pending_review → approved → sent/filed
                          │
                          └─→ rejected
```

### Steps

1. **View pending approvals**
   ```bash
   curl "http://localhost:8050/approvals?status=pending_review" \
     -H "X-Persona: in_house_counsel"
   ```

2. **Review document/action**
   - Check QA report
   - Verify content hash matches
   - Review any warnings

3. **Approve or Reject**
   ```bash
   # Approve
   curl -X POST http://localhost:8050/approvals/{id}/approve \
     -H "X-Persona: in_house_counsel" \
     -d '{"notes": "Reviewed and approved"}'
   
   # Reject
   curl -X POST http://localhost:8050/approvals/{id}/reject \
     -H "X-Persona: in_house_counsel" \
     -d '{"reason": "Missing required disclosure"}'
   ```

4. **Verify execution**
   - After action is performed, check final status
   - Verify content hash matches approved version

---

## Running Regression Tests

### Before Deployment

```bash
cd backend

# Run full test suite
pytest tests/test_*.py -v

# Run AI-first module tests
pytest tests/test_requirements_ops.py
pytest tests/test_citations.py
pytest tests/test_approvals.py
pytest tests/test_eval_harness.py

# Run state pack contract tests
python -c "
from app.services.eval_harness import EvalHarness
harness = EvalHarness()
for state in ['TX', 'CA', 'FL', 'MI', 'MO']:
    result = harness.validate_state_pack(state)
    print(f'{state}: {'PASS' if result['pack_valid'] else 'FAIL'}')
"
```

### After State Pack Update

```bash
python -c "
from app.services.eval_harness import EvalHarness, generate_uat_checklist
harness = EvalHarness()

# Validate specific state
validation = harness.validate_state_pack('TX')
if not validation['pack_valid']:
    print('CRITICAL FAILURES:')
    for f in validation['critical_failures']:
        print(f'  - {f}')

# Generate UAT checklist
checklist = generate_uat_checklist('TX')
print(checklist)
"
```

---

## Investigating AI Failures

### Gathering Evidence

1. **Get the AI event**
   ```bash
   curl http://localhost:8050/audit/ai-events/{event_id} \
     -H "X-Persona: admin"
   ```

2. **Check inputs/outputs**
   - Review `inputs_json` for what was sent
   - Review `outputs_json` for what was received
   - Verify hashes match

3. **Get replay configuration**
   ```bash
   curl http://localhost:8050/audit/ai-events/{event_id}/replay \
     -H "X-Persona: admin"
   ```

4. **Check related citations**
   ```bash
   curl http://localhost:8050/audit/citations/ai_decision/{decision_id} \
     -H "X-Persona: admin"
   ```

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Low confidence | Insufficient context | Add more retrieval sources |
| Missing citations | Prompt issue | Update prompt template |
| Wrong deadline | Rule misconfiguration | Fix state pack |
| High latency | Token limit | Optimize prompt |

---

## Managing Citations and Sources

### Adding a New Source

```bash
curl -X POST http://localhost:8050/audit/sources \
  -H "X-Persona: in_house_counsel" \
  -d '{
    "title": "Texas Property Code Chapter 21",
    "jurisdiction": "TX",
    "authority_level": "statute",
    "citation_string": "Tex. Prop. Code Ch. 21",
    "raw_text": "Section 21.0112..."
  }'
```

### Verifying Sources

```bash
curl -X POST http://localhost:8050/audit/sources/{id}/verify \
  -H "X-Persona: in_house_counsel" \
  -d '{"notes": "Verified against official Westlaw publication"}'
```

### Checking Citation Coverage

```bash
# Check all citations for an AI decision
curl http://localhost:8050/audit/citations/ai_decision/{decision_id} \
  -H "X-Persona: in_house_counsel"

# Verify citations in output
curl -X POST http://localhost:8050/audit/citations/verify \
  -H "X-Persona: in_house_counsel" \
  -d '{"claims": [...]}'
```

---

## Cost Monitoring

### View Cost Summary

```bash
# Overall costs
curl http://localhost:8050/audit/costs \
  -H "X-Persona: admin"

# By project
curl "http://localhost:8050/audit/costs?project_id=PRJ-001" \
  -H "X-Persona: admin"

# Since date
curl "http://localhost:8050/audit/costs?since=2026-01-01" \
  -H "X-Persona: admin"
```

### Cost Breakdown

Response format:
```json
{
  "total_cost_usd": "12.34",
  "total_events": 500,
  "total_input_tokens": 1000000,
  "total_output_tokens": 250000,
  "by_model": {
    "gemini-1.5-pro": "10.00",
    "gemini-1.5-flash": "2.34"
  },
  "by_action": {
    "generate_draft": "5.00",
    "evaluate_compliance": "3.00",
    "analyze_title": "4.34"
  }
}
```

### Budget Alerts

Set up monitoring for:
- Daily cost exceeding threshold
- Single operation cost spikes
- Token usage patterns

---

## Emergency Procedures

### Reverting a State Pack

1. **Check archive**
   ```bash
   ls rules/archive/
   ```

2. **Restore previous version**
   ```bash
   cp rules/archive/tx_20260128_120000.yaml rules/tx.yaml
   ```

3. **Re-import and publish**
   ```bash
   # Import archived version
   curl -X POST http://localhost:8050/rules/import_state_pack ...
   curl -X POST http://localhost:8050/rules/publish ...
   ```

### Stopping AI Operations

If AI is producing incorrect outputs:

1. **Check escalation queue**
   - Review pending escalations
   - Identify pattern

2. **Temporarily increase thresholds**
   - Raise confidence threshold to force human review
   - All decisions will require manual approval

3. **Investigate root cause**
   - Check prompt templates
   - Review retrieval sources
   - Verify state pack accuracy

4. **Fix and test**
   - Update configuration
   - Run regression tests
   - Deploy fix
   - Restore normal thresholds
