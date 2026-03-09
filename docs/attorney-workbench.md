# Attorney Workbench

- **Approvals Queue**: `GET /workflows/approvals` drives the dashboard showing pending template reviews, binder exports, and filing gates.
- **Tasks**: `POST /workflows/tasks` creates persona-specific tasks with due dates + SLA for escalation.
- **Binder Export**: `POST /workflows/binder/export` generates immutable PDF+JSON, hashes output, and logs AuditEvent.
- **Budget Board**: Tied to `Budget` table; alerts when utilization >80% and requires justification at 100%.
- **Outside Counsel Handoff**: Binder export metadata includes `bundle_id` for repository completeness check before sharing.
- **UI**: See `/counsel` route in Next.js app for visualization of queue, budget, binder readiness.
