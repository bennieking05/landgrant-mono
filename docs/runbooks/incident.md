# Incident Response

**Roles**: Primary on-call (infra), Secondary (backend), Legal liaison (counsel) for SEV1 deadline risk.

1. **Detect**: Alerts from Cloud Monitoring, Sentry, or PagerDuty.
2. **Triage**: On-call classifies severity (**SEV1**: legal deadline or data-loss risk, **SEV2**: broad user impact, **SEV3**: localized/minor).
3. **Mitigate**: Engage domain owners (infra, backend, counsel). Pause deployments if SLO breach or suspected bad release.
4. **Communicate**: Status page + pilot partners every 30 minutes for SEV1/2; internal Slack thread with timeline.
5. **Resolve**: Verify fixes, capture deploy SHA, close incident in PagerDuty.
6. **Postmortem**: Within 48 hours, blameless review with timeline, root cause, and tracked action items; attach log links (Cloud Logging) and Sentry issue URLs.

**Postmortem template**: summary, impact, detection gap, remediation, prevention follow-ups (owner + due date).
