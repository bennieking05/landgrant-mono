# k6 API checks (Phase 2)

Non-functional targets in `docs/nonfunctional.md` call for API P95 &lt; 300ms once traffic patterns are stable.

## Local

```bash
brew install k6   # or apt per .github/workflows/k6-nightly.yml
k6 run scripts/k6/api-smoke.js -e BASE_URL=http://localhost:8050
```

## CI

Workflow `.github/workflows/k6-nightly.yml` runs weekly and on `workflow_dispatch`. Set repository secret `STAGING_API_BASE_URL` for checks against staging; otherwise the job skips the run.

Thresholds start conservative (`p(95)<800` ms) and should be tightened toward 300ms after baselines exist.
