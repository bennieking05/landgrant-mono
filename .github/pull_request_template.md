## Summary

<!-- Brief description of changes -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Configuration change

## Related Issues

<!-- Link to related issues: Fixes #123, Relates to #456 -->

---

## Quality Gate Checklist (REQUIRED)

### Regression Testing

- [ ] I ran Playwright regression locally
  - Command: `cd frontend && npm run test:e2e`
- [ ] All tests passed (0 failures)
- [ ] No tests were skipped (or skips are justified below)

### Evidence Screenshots

- [ ] I captured screenshots for impacted flows
  - Command: `cd frontend && npm run test:evidence`
- [ ] Screenshots are attached or path provided below
- [ ] Both desktop and mobile viewports included

### Code Quality

- [ ] No console errors observed during testing
- [ ] Code follows project style guidelines
- [ ] Self-review completed

---

## Evidence Summary

<!-- 
REQUIRED: Paste your evidence summary here.
Run `npm run test:regression` to generate this.
-->

```
✅ Regression Suite: PASSED / FAILED
🧪 Total Tests: <number>
❌ Failures: 0
⏭️ Skips: 0
⚠️ Console Errors: 0
📸 Screenshots Captured: <number>
📁 Evidence Location: frontend/tests/regression-screenshots/<feature>/<timestamp>/
🕒 Timestamp: <ISO-8601>
```

### Test Results

<!-- Paste test output summary -->

### Screenshots Location

<!-- Path to screenshots or attach images -->

---

## Skip Justification (if applicable)

<!-- If any tests were skipped, explain why here -->

---

## Additional Notes

<!-- Any other context for reviewers -->
