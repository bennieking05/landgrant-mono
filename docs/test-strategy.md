# Test Strategy

- **Unit Tests**: Rules engine fixtures (`backend/tests/rules/`), template variable validation, RBAC policies, utility functions.
- **Contract Tests**: Mock ESRI, Adobe Sign, SendGrid, Twilio, Lob, OCR, calendar APIs with Pact-like expectations. Run in CI.
- **Integration Tests**: Spin up Postgres + Redis via docker-compose; exercise FastAPI endpoints end-to-end.
- **E2E**: Playwright scenarios per persona (landowner invite→e-sign, agent generating pre-offer, counsel approving binder, outside counsel initiating case).
- **Synthetic Monitoring**: Cloud Scheduler hits `/health/invite`, `/health/esign`, `/health/docket` endpoints to simulate flows.
- **Security / Red-team**: Scripts attempt privilege escalation, row-level bypass, and injection. Run before pilot.
