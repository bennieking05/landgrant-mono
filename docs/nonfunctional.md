# Non-Functional Requirements

- **Performance**: API P95 < 300 ms, streaming map renders (<2 s for 1k parcels). Celery tasks SLA < 2 min for packet generation.
- **Uptime**: 99.5% monthly. Error budget triggers release freeze + incident review.
- **Accessibility**: WCAG 2.1 AA; keyboard navigation, focus outlines, high-contrast mode, screen reader labels.
- **Internationalization**: EN/ES scaffolding; locale negotiation by Accept-Language header.
- **Scalability**: Multi-tenant isolation via row-level policies and namespace segmentation; LaunchDarkly flags for progressive rollout.
- **Security**: TLS 1.2+, MFA, SSO, DPAs, encryption at rest, hashed exports.
- **Observability**: OpenTelemetry traces, metrics (settle-rate, time-to-decision, packet error %), Sentry for front/back.
