import { Link, useLocation } from "react-router-dom";
import { useAppContext, type Persona } from "@/context";

const stages = [
  {
    title: "Landowner Portal",
    description: "Secure invite, document review, uploads, and accept or counter with e-sign.",
    href: "/portal",
    personas: ["landowner", "platform_admin"] as Persona[],
  },
  {
    title: "Agent Workbench",
    description: "Parcel map, comms log, pre-offer packet generation, title, and tasks.",
    href: "/workbench",
    personas: ["land_agent", "in_house_counsel", "platform_admin"] as Persona[],
  },
  {
    title: "Counsel Controls",
    description: "Template approvals, binder exports, deadlines, litigation, and AI review.",
    href: "/counsel",
    personas: ["in_house_counsel", "outside_counsel", "platform_admin"] as Persona[],
  },
  {
    title: "Operations",
    description: "Route planning, batch notifications, integration status, field coordination.",
    href: "/ops",
    personas: ["land_agent", "in_house_counsel", "platform_admin"] as Persona[],
  },
];

const adminStages = [
  {
    title: "Firm Admin",
    description: "Rolled-up cases across your firm's projects with metrics and activity.",
    href: "/firm-admin",
    personas: ["firm_admin", "platform_admin"] as Persona[],
  },
  {
    title: "Platform Admin",
    description: "System-wide dashboard, global search, health, and AI decision metrics.",
    href: "/admin",
    personas: ["platform_admin"] as Persona[],
  },
];

export function HomePage() {
  const { persona } = useAppContext();
  const location = useLocation();
  const redirected =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state;

  const visibleStages = stages.filter((s) => s.personas.includes(persona));
  const visibleAdmin = adminStages.filter((s) => s.personas.includes(persona));

  return (
    <section className="space-y-8">
      <header>
        <p className="text-sm uppercase tracking-wide text-brand">LandGrant MVP</p>
        <h1 className="mt-2 text-4xl font-semibold text-slate-900">Attorney-in-the-loop automation</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-600">
          Workspaces below match your signed-in role. Use Logout to switch accounts.
        </p>
        {redirected ? (
          <p className="mt-3 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 max-w-xl">
            That page is not available for your current persona. Choose a workspace you have access to.
          </p>
        ) : null}
      </header>

      {/* Quick summary */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Persona</p>
          <p className="mt-1 text-lg font-semibold text-slate-900 capitalize">{persona.replace(/_/g, " ")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Workspaces</p>
          <p className="mt-1 text-lg font-semibold text-slate-900">{visibleStages.length}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Admin areas</p>
          <p className="mt-1 text-lg font-semibold text-slate-900">{visibleAdmin.length}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {visibleStages.map((stage) => (
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

      {visibleAdmin.length > 0 ? (
        <div className="pt-4 border-t border-slate-200">
          <h3 className="text-lg font-semibold text-slate-700 mb-4">Administration</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {visibleAdmin.map((stage) => (
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
      ) : null}
    </section>
  );
}
