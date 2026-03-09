# Documented Legal Boundaries

- UI banner on every decision-support panel: “This workflow assists counsel but is not legal advice; filings require attorney approval.”
- Attorney sign-off required before any outbound filing, notice, or budget commitment (workflow enforced via `Task` + `Approval` tables).
- No appraisal opinions: system ingests third-party appraisals, calculates comps, but does not produce new valuations.
- Kovel arrangements supported via privilege tags; law firm specific workflows (LawCo) segregated with data isolation + Workspaces.
- Automated recommendations always include citation + rule version; counsel may override with justification captured in audit log.
