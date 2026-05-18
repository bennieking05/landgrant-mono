# Test Strategy

> **This document has moved.** The canonical testing strategy now lives in
> [testing-strategy.md](./testing-strategy.md). This stub is kept only so
> older `.cursorrules` / README links resolve; please update any references
> you own to point at the new file.
>
> Summary of the split that used to live here (kept for quick reference):
>
> - **Unit Tests** — rules engine, template validation, RBAC policies.
> - **Contract Tests** — mocked ESRI, Adobe Sign, SendGrid, Twilio, Lob, OCR,
>   calendar APIs. Run in CI.
> - **Integration Tests** — Postgres + Redis via `docker-compose` exercising
>   FastAPI routes end-to-end.
> - **E2E** — Playwright per persona (landowner invite → e-sign, agent
>   pre-offer, counsel binder approval, outside counsel case intake).
> - **Synthetic Monitoring** — Cloud Scheduler probes against
>   `/health/invite`, `/health/esign`, `/health/docket`.
> - **Security / Red-team** — privilege escalation, row-level bypass, and
>   injection scripts run before pilot.

Go to [testing-strategy.md](./testing-strategy.md) for the current,
authoritative version (coverage targets, artifact locations, CI wiring).
