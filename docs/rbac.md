# Personas & Permissions

The matrix below is derived from the User Journeys swimlane, EminentAI backlog, and the final instructions provided for MVP scope.

| Action / Resource | Landowner | Land Agent | In-House Counsel | Outside Counsel |
|-------------------|-----------|-----------|------------------|-----------------|
| View assigned projects/parcels | ✅ (read-only) | ✅ | ✅ | ✅ (assigned parcels only) |
| Upload evidence, chat, accept/counter offers | ✅ | 🚫 | 🚫 | 🚫 |
| Parcel CRUD, comms log entries, packet generation | 🚫 | ✅ | 🚫 | 🚫 |
| Template creation/edit | 🚫 | 🚫 | ✅ (approver) | 🚫 |
| Template execution / packet export | 🚫 | ✅ (pre-offer) | ✅ (litigation) | ✅ (assigned cases) |
| Approve filings / legal decisions | 🚫 | 🚫 | ✅ | ✅ (after delegation) |
| Budget visibility & updates | 🚫 | 🚫 | ✅ | ✅ (variance reports only) |
| Rule overrides | 🚫 | 🚫 | ✅ (with audit justification) | 🚫 |
| Case status changes | Limited to Accept/Counter/E-sign | ✅ | ✅ | ✅ (must provide reason) |
| Admin (RBAC, configs) | 🚫 | 🚫 | ✅ (subset) | 🚫 |

Implementation references:
- `backend/app/security/rbac.py` enumerates permissions as enums -> Postgres row-level policies.
- `docs/security.md` explains least-privilege, SSO/MFA enforcement, and privilege escalation logs.
