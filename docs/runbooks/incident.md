# Incident Response

1. **Detect**: Alerts from Cloud Monitoring/Sentry/PagerDuty.
2. **Triage**: On-call classifies severity (SEV1: legal deadline risk, SEV2: user-impacting, SEV3: minor).
3. **Mitigate**: Engage domain owners (infra, backend, counsel). Pause deployments if SLO breach.
4. **Communicate**: Update status page + pilot partners every 30m for SEV1/2.
5. **Resolve**: Verify fixes + close incident in PagerDuty.
6. **Postmortem**: Within 48h, run blameless review, document action items, attach logs + metrics.
