# Functional Gap Closure

> Gaps identified and closed during the March 2026 audit.

## Summary

Multiple runtime crashes, broken features, and missing functionality were identified and fixed.

---

## Gaps Closed

### 1. Runtime Crashes Fixed

| Bug | File | Fix |
|-----|------|-----|
| `Action.UPDATE` not in enum | `rbac.py` | Added `CREATE`, `UPDATE`, `DELETE` to Action enum |
| `Action.CREATE` not in enum | `rbac.py` | Same as above |
| `Action.DELETE` not in enum | `rbac.py` | Same as above |
| `user.get("sub")` on ORM object | `admin.py` | Changed to `user.id if hasattr(user, "id") else "unknown"` |

### 2. RBAC Resources Added

| Resource | Personas with access | Action types |
|----------|---------------------|--------------|
| `rules` | agent (R), counsel (RW), outside_counsel (R), admin (RW) | READ, WRITE |
| `qa` | counsel (RW), admin (RW) | READ, WRITE |
| `approvals` | counsel (RWA), admin (RWA) | READ, WRITE, APPROVE |
| `task` | agent (RCU), counsel (RCUD), admin (RCUD), firm_admin (R), outside_counsel (R) | READ, CREATE, UPDATE, DELETE |
| `rag` | counsel (R), admin (RW) | READ, WRITE |
| `copilot` | counsel (RW), admin (RW) | READ, WRITE |
| `analytics` | counsel (R), admin (R) | READ |
| `predictions` | counsel (R), admin (R) | READ |

### 3. Binder Export Data Leak Fixed

Documents query now filters by `project_id` instead of loading all documents.

### 4. Seven Components Wired

ROEPanel, NegotiationPanel, TaskManager, LitigationPanel, NotificationBell, AIDecisionDashboard all wired into their appropriate pages.

### 5. API Base URL Standardized

`TaskManager.tsx` was using `VITE_API_URL`. Fixed to `VITE_API_BASE`.

---

## Gaps Remaining

| Gap | Priority | Description |
|-----|----------|-------------|
| Portal file uploads use local disk | P2 | Should use GCS in production |
| No login/session UI | P2 | Stub auth, no SSO integration |
| Hard-coded demo projects | P3 | AppContext has static project list |
| WebSocket user_id trust | P2 | Client-supplied, not server-validated |
| No Alembic migrations | P2 | Using `create_all` on startup |
| No frontend error boundaries | P3 | Uncaught errors crash the entire app |
| No rate limiting | P2 | API endpoints have no abuse protection |
