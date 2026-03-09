# Quality Gates

This document describes the quality gates enforced in the LandRight repository.

## Overview

LandRight enforces a **mandatory quality gate** that requires:

1. **Playwright regression tests** must pass (0 failures)
2. **Evidence screenshots** must be captured for UI changes
3. **Evidence summary** must be documented

These gates are enforced at multiple levels:
- **Cursor Agent Rule** - AI assistant refuses to mark work complete without verification
- **Pre-push Hook** - Git blocks pushes if tests fail
- **PR Template** - Requires evidence checklist before merge
- **CI Pipeline** - Runs full regression on all PRs

---

## Running Tests

### Quick Reference

```bash
# Navigate to frontend
cd frontend

# Run full regression suite
npm run test:e2e

# Run evidence screenshots only
npm run test:evidence

# Run full regression + evidence
npm run test:regression

# Run smoke tests (faster, used by pre-push hook)
npm run test:smoke

# Run with visible browser
npm run test:e2e:headed

# Debug mode (step through)
npm run test:e2e:debug

# View HTML report
npm run test:e2e:report
```

### Test Commands Explained

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `test:e2e` | Full regression suite | Before marking work complete |
| `test:evidence` | Capture screenshots | For UI changes |
| `test:regression` | Full regression + evidence | Comprehensive verification |
| `test:smoke` | Quick validation | Pre-push hook, quick checks |

---

## Evidence Screenshots

### Where Screenshots Are Stored

```
frontend/tests/regression-screenshots/
  └── <feature-name>/
      └── <timestamp>/
          ├── 01-homepage-desktop.png
          ├── 01-homepage-mobile.png
          ├── 02-case-list-desktop.png
          ├── 02-case-list-mobile.png
          └── ...
```

### Controlling Screenshot Location

Use environment variables to customize the output:

```bash
# Set feature name
FEATURE_NAME=my-feature npm run test:evidence

# Set specific timestamp
EVIDENCE_TS=2024-01-15T10-30-00 npm run test:evidence
```

### Adding New Screenshots

To add screenshots for a new flow, edit:
`frontend/tests/evidence/core-flows.spec.ts`

Example:

```typescript
test('My New Flow', async ({ page }) => {
  await page.goto('/my-route');
  await page.waitForLoadState('networkidle');
  
  const { desktop, mobile } = await captureResponsiveScreenshots(page, '15-my-flow');
  collectedScreenshots.push(desktop, mobile);
});
```

---

## Git Hooks

### Installing Hooks

```bash
./scripts/install-githooks.sh
```

This sets up the pre-push hook that runs smoke tests before every push.

### What the Pre-push Hook Does

1. Runs `npm run test:smoke` in the frontend directory
2. If tests pass → push allowed
3. If tests fail → push blocked with error message

### Bypassing the Hook (Emergency Only)

```bash
git push --no-verify
```

**WARNING:** Only use this for true emergencies. You must document why in your PR.

### Uninstalling Hooks

```bash
git config --unset core.hooksPath
```

---

## CI Pipeline

### Workflow

The CI pipeline (`landright-ci`) runs on:
- All pushes to `main`
- All pull requests to `main`

### Jobs

1. **validate** - Linting and unit tests (Python + TypeScript)
2. **playwright** - Full Playwright regression suite

### Artifacts

After each CI run, these artifacts are uploaded:
- `playwright-report` - HTML test report
- `playwright-results` - Test result files
- `evidence-screenshots` - Captured screenshots

Artifacts are retained for 30 days.

---

## PR Requirements

Every PR must include the evidence summary block:

```
## Evidence Summary

✅ Regression Suite: PASSED
🧪 Total Tests: <number>
❌ Failures: 0
⏭️ Skips: 0
⚠️ Console Errors: 0
📸 Screenshots Captured: <number>
📁 Evidence Location: frontend/tests/regression-screenshots/<feature>/<timestamp>/
🕒 Timestamp: <ISO-8601>
```

The PR template includes a checklist that must be completed.

---

## Troubleshooting

### Tests Won't Run

1. Ensure you're in the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Install Playwright browsers:
   ```bash
   npx playwright install
   ```

### Tests Fail in CI but Pass Locally

1. Check for race conditions - add `await page.waitForLoadState('networkidle')`
2. Check for viewport differences - CI uses headless browser
3. Check for timing issues - add appropriate waits

### Screenshots Are Missing

1. Ensure the evidence test ran:
   ```bash
   npm run test:evidence
   ```

2. Check the output directory:
   ```bash
   ls frontend/tests/regression-screenshots/
   ```

### Pre-push Hook Not Running

1. Verify hooks are installed:
   ```bash
   git config core.hooksPath
   ```

2. Re-install if needed:
   ```bash
   ./scripts/install-githooks.sh
   ```

---

## Quick Checklist

Before marking any work complete:

- [ ] `npm run test:e2e` passes (0 failures)
- [ ] `npm run test:evidence` captures screenshots (for UI changes)
- [ ] Evidence summary block is prepared
- [ ] No console errors observed
- [ ] Pre-push hook is installed (`./scripts/install-githooks.sh`)
