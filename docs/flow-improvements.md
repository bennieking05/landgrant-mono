# Flow Improvements

> UX and workflow improvements implemented during the March 2026 platform audit.

## Summary

The frontend was restructured from a flat collection of screens into a persona-aware, step-driven legal operations platform.

---

## Changes Made

### 1. Persona-Aware Navigation

**Problem**: All nav items were visible to all users. A landowner could see Admin, Workbench, and Counsel pages.

**Fix**: Added `personaNavMap` in `AppLayout.tsx` that maps each persona to their allowed nav paths:

| Persona | Allowed Pages |
|---------|--------------|
| Landowner | Home, Intake |
| Land Agent | Home, Workbench, Operations |
| In-House Counsel | Home, Workbench, Counsel, Operations |
| Outside Counsel | Home, Counsel |
| Firm Admin | Home, Firm Admin |
| Admin | All pages |

A persona selector dropdown was added to the nav bar so users can switch context during development and testing.

### 2. Landowner Portal Step Progression

**Problem**: IntakePage showed all components in a flat grid with no guidance.

**Fix**: Transformed into a 4-step wizard:
1. **Verify Identity** -- InviteCard for token-based access
2. **Review Documents** -- ParcelMap for spatial context
3. **Upload Materials** -- UploadPanel with progress feedback
4. **Make Decision** -- DecisionActions (Accept / Counter / Request Callback)

Agent tools (IntakeForm, AIDraftPanel) are in a collapsible section below the wizard.

### 3. Wired Orphan Components

Seven built-but-unused components now appear in the appropriate pages:

| Component | Page |
|-----------|------|
| ROEPanel | Workbench (title/appraisal grid) |
| NegotiationPanel | Workbench (after grid) |
| TaskManager | Workbench + Counsel (bottom) |
| LitigationPanel | Counsel (after outside counsel) |
| NotificationBell | Nav bar (all pages) |
| AIDecisionDashboard | Admin (new tab) |

### 4. Persona State in Context

**Problem**: No persona awareness in the frontend state.

**Fix**: Added `persona` and `setPersona` to `AppContext`. Default is `land_agent`. Components can now conditionally render based on persona.

---

## Remaining Work

- Add route-level guards that redirect unauthorized personas (currently nav filtering only)
- Add empty states to all list views
- Add loading skeletons to all data-fetching components
- Add error boundaries around each major section
- Improve mobile responsiveness on tablet breakpoints
- Add breadcrumbs for detail views (parcel detail, case detail)
- Add dashboard summary cards to HomePage per persona
