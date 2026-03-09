import { Link } from "react-router-dom";

const stages = [
  {
    title: "Landowner Portal",
    description: "Secure invite → document review → chat/uploads → accept/counter/e-sign",
    href: "/intake",
  },
  {
    title: "Agent Workbench",
    description: "Parcel list/map, comms log, pre-offer packet generation with tracking",
    href: "/workbench",
  },
  {
    title: "Counsel Controls",
    description: "Template approvals, binder exports, deadlines, budgets, outside counsel handoff",
    href: "/counsel",
  },
  {
    title: "Operations",
    description: "Route planning, batch notifications, integration status, field coordination",
    href: "/ops",
  },
];

const adminStages = [
  {
    title: "Firm Admin",
    description: "Rolled-up view of all cases across your firm's projects with metrics and activity",
    href: "/firm-admin",
  },
  {
    title: "Platform Admin",
    description: "System-wide dashboard with global search, all cases, projects, and health status",
    href: "/admin",
  },
];

export function HomePage() {
  return (
    <section className="space-y-8">
      <header>
        <p className="text-sm uppercase tracking-wide text-brand">LandRight MVP</p>
        <h1 className="mt-2 text-4xl font-semibold text-slate-900">Attorney-in-the-loop automation</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-600">
          Built from the LandRight-AI dossier, EminentAI backlog, and swimlane journeys. Choose a workspace below to
          explore the MVP flows.
        </p>
      </header>

      {/* Main Workspaces */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stages.map((stage) => (
          <Link
            key={stage.title}
            to={stage.href}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand hover:shadow-md"
          >
            <h2 className="text-xl font-semibold text-slate-900">{stage.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{stage.description}</p>
          </Link>
        ))}
      </div>

      {/* Admin Section */}
      <div className="pt-4 border-t border-slate-200">
        <h3 className="text-lg font-semibold text-slate-700 mb-4">Administration</h3>
        <div className="grid gap-4 md:grid-cols-2">
          {adminStages.map((stage) => (
            <Link
              key={stage.title}
              to={stage.href}
              className="rounded-xl border border-slate-200 bg-slate-50 p-6 shadow-sm transition hover:border-brand hover:shadow-md"
            >
              <h2 className="text-xl font-semibold text-slate-900">{stage.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{stage.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}



