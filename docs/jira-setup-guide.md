# Jira Setup Guide

> **Purpose**: Configure Jira for LandRight MVP backlog management  
> **Created**: January 24, 2026  
> **Backlog Source**: `/docs/backlog/landright_backlog.csv`

---

## Prerequisites

- Jira Cloud or Server admin access
- CSV import permissions
- Project creation permissions

---

## Step 1: Create Project

1. Navigate to **Projects** → **Create project**
2. Select **Scrum** template (recommended) or **Kanban**
3. Configure:
   - **Name**: LandRight MVP
   - **Key**: LRMVP
   - **Lead**: [Assign project lead]

---

## Step 2: Configure Issue Types

Ensure these issue types exist (create if needed):

| Issue Type | Description |
|------------|-------------|
| Epic | High-level feature grouping (Agreement section) |
| Story | User story with acceptance criteria |
| Task | Technical or non-functional work |
| Sub-task | Breakdown of stories/tasks |
| Bug | Defects found during development/UAT |

---

## Step 3: Create Custom Fields

Navigate to **Settings** → **Issues** → **Custom fields** → **Create custom field**

### Required Custom Fields

| Field Name | Type | Options/Config |
|------------|------|----------------|
| Milestone | Select List (single) | M1, M2, M3, M4, M5 |
| Agreement Reference | Text Field (single line) | For Section 3.2(x) refs |
| Fee Allocation | Number Field | For milestone fee tracking |

### Milestone Field Values

```
M1 - Technical Design & Backlog Refinement
M2 - Backend MVP API
M3 - Frontend Internal Web App
M4 - Landowner Portal & Comms
M5 - UAT & Production-Ready
```

### Add Fields to Screens

1. Go to **Settings** → **Issues** → **Screens**
2. Edit the default screen scheme
3. Add custom fields to:
   - Create Issue Screen
   - Edit Issue Screen
   - View Issue Screen

---

## Step 4: Create Epics

Before importing stories, create the 17 Epics manually:

```
LRMVP-1: Projects & Parcels
LRMVP-2: Notices & Service (Legal Playbooks)
LRMVP-3: Right-of-Entry (ROE) Management
LRMVP-4: Litigation & Case Deadline Calendar
LRMVP-5: Title & Curative Tracking
LRMVP-6: Payment & Negotiation Module
LRMVP-7: Landowner Portal
LRMVP-8: Communications
LRMVP-9: Documents & Templates
LRMVP-10: GIS Alignment & Segmentation
LRMVP-11: Analytics & Reporting
LRMVP-12: Authentication & Authorization
LRMVP-13: Audit & Security
LRMVP-14: Email Integration
LRMVP-15: Technical Design (Milestone 1)
LRMVP-16: UAT & Hardening (Milestone 5)
LRMVP-17: Out of Scope (MVP Exclusions)
```

### Epic Creation Script (Optional)

For bulk creation via Jira CLI or API:

```bash
# Using Jira CLI (if installed)
jira epic create -p LRMVP -s "Projects & Parcels" -d "Core project and parcel management - Section 3.2(a)"
jira epic create -p LRMVP -s "Notices & Service (Legal Playbooks)" -d "Notice and service tracking - Section 3.2(b)"
# ... repeat for all epics
```

---

## Step 5: Import Backlog CSV

### Prepare CSV

The import file is located at: `/docs/backlog/landright_backlog.csv`

CSV columns:
- Issue Type
- Summary
- Description
- Epic Link
- Labels
- Milestone

### Import Steps

1. Navigate to **Project Settings** → **External System Import**
2. Select **CSV**
3. Upload `landright_backlog.csv`
4. Map columns:

| CSV Column | Jira Field |
|------------|------------|
| Issue Type | Issue Type |
| Summary | Summary |
| Description | Description |
| Epic Link | Epic Link (select by name) |
| Labels | Labels |
| Milestone | Milestone (custom field) |

5. Run **Dry Run** first to validate
6. Review mapping results
7. Execute import

### Post-Import Validation

After import, verify:
- [ ] All 72 stories imported
- [ ] Stories linked to correct Epics
- [ ] Milestone field populated
- [ ] Labels applied correctly

---

## Step 6: Configure Board

### Create Scrum Board

1. Navigate to **Boards** → **Create board**
2. Select **Scrum board**
3. Choose **Board from an existing project**: LRMVP

### Configure Columns

Default columns for MVP workflow:

| Column | Statuses |
|--------|----------|
| Backlog | Open |
| Selected for Sprint | Selected |
| In Progress | In Progress |
| In Review | In Review |
| Done | Done, Closed |

### Configure Swimlanes

Set swimlanes by **Epic** for better visualization.

---

## Step 7: Create Filters

Create saved filters for tracking:

### By Milestone

```jql
project = LRMVP AND Milestone = M1
project = LRMVP AND Milestone = M2
project = LRMVP AND Milestone = M3
project = LRMVP AND Milestone = M4
project = LRMVP AND Milestone = M5
```

### By Agreement Section

```jql
project = LRMVP AND Epic = "Projects & Parcels"
project = LRMVP AND Epic = "Notices & Service (Legal Playbooks)"
project = LRMVP AND Epic = "Right-of-Entry (ROE) Management"
project = LRMVP AND Epic = "Litigation & Case Deadline Calendar"
project = LRMVP AND Epic = "Title & Curative Tracking"
project = LRMVP AND Epic = "Payment & Negotiation Module"
project = LRMVP AND Epic = "Communications"
project = LRMVP AND Epic = "GIS Alignment & Segmentation"
```

### Critical Views

```jql
# M1 Incomplete
project = LRMVP AND Milestone = M1 AND status != Done

# Out of Scope (should not be scheduled)
project = LRMVP AND labels = "out-of-scope"

# Backend work for M2
project = LRMVP AND Milestone = M2 AND labels = backend

# Frontend work for M3
project = LRMVP AND Milestone = M3 AND labels = frontend
```

---

## Step 8: Create Dashboard

### Add Gadgets

1. Go to **Dashboards** → **Create dashboard**
2. Name: "LandRight MVP Tracking"
3. Add gadgets:

| Gadget | Configuration |
|--------|---------------|
| Filter Results | Stories by Milestone |
| Pie Chart | Stories by Epic |
| Two Dimensional Filter | Milestone × Status |
| Sprint Burndown | Current sprint |
| Created vs Resolved | Last 30 days |

### Sample Dashboard Layout

```
┌─────────────────────────────┬─────────────────────────────┐
│ Milestone Progress          │ Stories by Epic             │
│ [Pie Chart]                 │ [Pie Chart]                 │
├─────────────────────────────┼─────────────────────────────┤
│ Sprint Burndown             │ Recent Activity             │
│ [Chart]                     │ [Activity Stream]           │
├─────────────────────────────┴─────────────────────────────┤
│ M1 Stories - Status                                       │
│ [Filter Results: Milestone = M1]                          │
└───────────────────────────────────────────────────────────┘
```

---

## Step 9: Configure Automation (Optional)

### Suggested Automation Rules

1. **Auto-assign on sprint start**
   - When: Issue moved to sprint
   - Then: Assign to default assignee

2. **Notify on milestone completion**
   - When: All issues in milestone = Done
   - Then: Send email to stakeholders

3. **Link acceptance criteria**
   - When: Story created
   - Then: Add comment template for AC verification

---

## Step 10: Validate Agreement Traceability

### Verification Checklist

Run these queries to verify complete coverage:

| Agreement Section | JQL | Expected Count |
|-------------------|-----|----------------|
| 3.2(a) Projects/Parcels | `Epic = "Projects & Parcels"` | 3 stories |
| 3.2(b) Notices/Service | `Epic = "Notices & Service"` | 4 stories |
| 3.2(c) ROE | `Epic = "Right-of-Entry"` | 4 stories |
| 3.2(d) Litigation | `Epic = "Litigation & Case Deadline"` | 5 stories |
| 3.2(e) Title/Curative | `Epic = "Title & Curative"` | 5 stories |
| 3.2(f) Payment | `Epic = "Payment & Negotiation"` | 4 stories |
| 3.2(g) Communications | `Epic = "Communications"` | 5 stories |
| 3.2(h) GIS | `Epic = "GIS Alignment"` | 4 stories |

### Total Story Count by Milestone

| Milestone | Expected Stories |
|-----------|-----------------|
| M1 | 3 |
| M2 | 32 |
| M3 | 12 |
| M4 | 15 |
| M5 | 5 |
| Out of Scope | 4 |
| **Total** | **72** (excluding out-of-scope) |

---

## Appendix: CSV Column Mapping Reference

```
landright_backlog.csv structure:

Issue Type,Summary,Description,Epic Link,Labels,Milestone
Epic,"Projects & Parcels","Core project and parcel management...",,scope-mvp exhibit-a,
Story,"Create and Manage Projects","As a ROW Manager...",Projects & Parcels,milestone-2 scope-mvp,M2
Story,"Import and Manage Parcels","As a ROW Manager...",Projects & Parcels,milestone-2 scope-mvp,M2
...
```

---

## Support

For import issues:
- Verify CSV encoding (UTF-8)
- Check Epic names match exactly
- Ensure custom fields exist before import
- Use dry run to identify mapping errors

---

## Related Documents

- [Backlog (Markdown)](backlog/landright_backlog.md)
- [Backlog (CSV)](backlog/landright_backlog.csv)
- [Coverage Verification](backlog/coverage_verification.md)
