# Testing Strategy

> Testing approach and coverage for the LandGrant platform.

## Current Test Infrastructure

### Backend
- **Framework**: pytest
- **Test location**: `backend/tests/`
- **Run command**: `cd backend && .venv/bin/python -m pytest`
- **Current passing tests**: 99

### Frontend
- **Type checking**: `npx tsc --noEmit` (clean)
- **E2E Framework**: Playwright (existing specs in `frontend/tests/`)
- **Lint**: ESLint via `npm run lint`

---

## Test Coverage

### RBAC Tests (`test_endpoints_rbac.py`)
- 13 parameterized endpoint tests covering persona-based access control
- Verifies correct HTTP status codes (200, 403, 422) per persona
- Tests invalid persona header rejection
- Tests request validation

### Security Hardening Tests (`test_security_hardening.py`) -- NEW
40 tests covering:

| Category | Count | What's tested |
|----------|-------|---------------|
| Security Headers | 3 | X-Content-Type-Options, X-Frame-Options, Referrer-Policy |
| Action Enum | 7 | All 7 Action members exist with correct values |
| Auth on Previously-Open Routes | 7 | RAG, Copilot, Analytics, Predictions reject unauthenticated requests |
| RBAC Matrix Completeness | 11 | New resources exist for counsel, admin, and agent |
| Webhook Integration | 2 | Docket webhook accepts in dev, esign health responds |
| Health Endpoints | 3 | Live, invite, esign remain open |
| Negative Tests | 7 | Landowner cannot access admin resources |

### RBAC Negative Tests (`test_rbac_negative.py`)
24 tests for privilege escalation prevention.

### Agent Tests (`test_agents.py`)
22 tests for AI agent pipeline (compliance, valuation, edge cases).

---

## Testing Principles

1. **RBAC tests for every new route**: Any route that adds `authorize()` must have a corresponding test
2. **Security-first testing**: Test that unauthenticated/wrong-persona requests are rejected before testing happy paths
3. **No mocking auth in integration tests**: Use the actual middleware pipeline
4. **Health endpoints always open**: Never add auth to health checks
5. **Attorney-in-the-loop preservation**: Test that AI routes require counsel/admin persona

---

## Recommended Future Tests

### High Priority
- Portal token lifecycle (creation, validation, expiration, revocation)
- Binder export project scoping (verify no cross-project documents)
- Workflow stage transitions (guard evaluation, escalation creation)
- Template rendering security (XSS prevention)

### Medium Priority
- Celery task execution (mock Redis, verify task dispatch)
- RAG search accuracy (verify citation extraction)
- Settlement prediction input validation
- Upload file type validation

### Low Priority
- Frontend Playwright tests for persona nav filtering
- Visual regression tests for step progression wizard
- Performance benchmarks for binder export with large document sets

---

## CI Integration

Tests should run in the GitHub Actions workflow (`.github/workflows/ci.yml`):

```yaml
- name: Backend tests
  run: cd backend && .venv/bin/python -m pytest --tb=short -q
  
- name: Frontend typecheck
  run: cd frontend && npx tsc --noEmit
```

Both must pass before merge to main.
