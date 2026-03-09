# QA Regression & Evidence Enforcement Rule

## NON-NEGOTIABLE POLICY (HARD STOP)

This rule enforces a **mandatory quality gate** for all work in this repository.

### You MUST NOT:
- Mark any task/issue/PR as "Done", "Complete", "Finished", or "Ready"
- Claim implementation is complete
- Recommend merge/push as final
- State work is ready for review

### UNTIL you have:
1. **Run Playwright regression successfully** (0 failures, 0 skips unless explicitly allowed)
2. **Captured screenshots as evidence** for impacted flows
3. **Produced a written Evidence Summary** including paths to artifacts

---

## Required Commands

Before marking any work complete, run:

```bash
# Navigate to frontend
cd frontend

# Run full regression suite
npm run test:e2e

# Run evidence screenshots (captures desktop + mobile for all flows)
npm run test:evidence

# OR run both together
npm run test:regression
```

---

## Evidence Requirements

### Screenshots Must Include:
- Desktop viewport (1280x720)
- Mobile viewport (375x667)
- All impacted user flows
- Error states (if applicable)

### Screenshot Naming Convention:
```
tests/regression-screenshots/<feature-or-branch>/<timestamp>/
  ├── 01-<flow>-desktop.png
  ├── 01-<flow>-mobile.png
  ├── 02-<flow>-desktop.png
  └── 02-<flow>-mobile.png
```

---

## Required Evidence Summary Block

After running tests, you MUST output this block:

```
## Evidence Summary

✅ Regression Suite: PASSED
🧪 Total Tests: <number>
❌ Failures: 0
⏭️ Skips: 0 (or explain why)
⚠️ Console Errors: 0
📸 Screenshots Captured: <number>
📁 Evidence Location: frontend/tests/regression-screenshots/<feature>/<timestamp>/
🕒 Timestamp: <ISO-8601 timestamp>

### Test Results
- Chromium: ✅ PASSED
- Mobile Chrome: ✅ PASSED (if applicable)

### Screenshots Taken
1. <screenshot-name>.png - <description>
2. <screenshot-name>.png - <description>
...
```

---

## If Tests Cannot Be Run

If you cannot run tests in the current environment, you MUST:

1. Implement the code changes
2. Provide exact commands the user must run locally
3. **Refuse to mark anything as complete**
4. Output: "⚠️ BLOCKED: Cannot mark complete until regression + evidence verified locally"

---

## Enforcement Mechanisms

This policy is enforced by:

1. **This Cursor Rule** - Agent must follow before marking complete
2. **Pre-push Git Hook** - Blocks pushes if regression fails
3. **PR Template Checklist** - Requires evidence before merge
4. **CI Pipeline** - Runs full regression on all PRs

---

## Exceptions

The only valid exceptions are:
- Documentation-only changes (no code)
- Configuration changes that don't affect runtime behavior
- Explicit user override with documented justification

Even with exceptions, you must state: "No regression required because: <reason>"

---

## Quick Reference

| Action | Command | Required? |
|--------|---------|-----------|
| Full regression | `npm run test:e2e` | ✅ Always |
| Evidence screenshots | `npm run test:evidence` | ✅ For UI changes |
| Both combined | `npm run test:regression` | ✅ Recommended |
| View report | `npm run test:e2e:report` | Optional |
| Debug mode | `npm run test:e2e:debug` | Optional |
