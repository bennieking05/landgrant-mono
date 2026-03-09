# ADR 0001 – Choose FastAPI + Next.js for MVP

- **Context**: Need rapid delivery for attorney-in-loop workflows with deterministic rules, heavy integrations, and real-time UI.
- **Decision**: Use FastAPI (Python) and Next.js (React) deployed on GKE with Terraform-managed infra.
- **Consequences**:
  - ✅ Mature ecosystem for rules/AI/LLM tooling in Python.
  - ✅ React ecosystem matches Landowner/Agent UX requirements (ESRI JS API compatibility).
  - ⚠️ Need to manage Python + Node toolchains in mono-repo.
