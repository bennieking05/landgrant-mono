# QA Checklist

1. **Landowner Flow**
   - Invite email delivered + link expiration enforced.
   - Parcel overview renders with map + timeline.
   - Uploads hashed + flagged for virus scanning.
   - Accept / Counter / Request Call triggers correct task + audit event.
2. **Agent Workbench**
   - Parcel filters by stage/risk/deadline.
   - Comms log entries display proof + SLA timers.
   - Pre-offer packet checklist cannot complete until all docs uploaded.
3. **Counsel Controls**
   - Template edit requires persona = in-house counsel.
   - Binder export hashed + stored; outside counsel limited to assigned parcels.
   - Budget alerts fire at 80%/100% utilization.
4. **Integrations**
   - ESRI map tokens refreshed.
   - E-sign webhook validated + stored.
   - Docket webhook receives sample payload + enqueues Pub/Sub.
5. **Non-Functional**
   - Load test 1k parcels (map <2s, API P95 <300ms).
   - Accessibility: keyboard navigation, screen readers, contrast mode.
   - Localization: toggle EN/ES scaffolding.
