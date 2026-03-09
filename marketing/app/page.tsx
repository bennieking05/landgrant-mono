const highlights = [
  {
    title: "Deterministic compliance",
    body: "50-state rules encoded in YAML with citations, binder hooks, and audit logs.",
  },
  {
    title: "Invite-to-e-sign journeys",
    body: "Landowner portal mirrors your swimlane with chat, uploads, counters, and signatures.",
  },
  {
    title: "Counsel-ready packets",
    body: "AI drafts stay attorney-in-the-loop with approvals, redlines, and immutable exports.",
  },
];

const logos = ["/logos/utility.svg", "/logos/pipeline.svg", "/logos/fiber.svg"];

export default function MarketingPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 px-6 py-16">
      <header className="mx-auto max-w-5xl text-center">
        <p className="text-sm uppercase tracking-[0.3em] text-brand-accent">LandRight Platform</p>
        <h1 className="mt-6 text-5xl font-semibold leading-tight text-white">
          Close right-of-way matters <span className="text-brand-accent">30% faster</span> with an attorney in the loop.
        </h1>
        <p className="mt-6 text-lg text-slate-200">
          LandRight unifies landowner invites, agent workbench tools, deterministic rule automation, and counsel approvals on top of GCP.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-sm text-slate-400">
          <span>GCP + Vertex AI</span>
          <span>Immutable Evidence</span>
          <span>ESRI-ready</span>
          <span>SOC 2 Controls</span>
        </div>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <a
            href="http://localhost:8080"
            className="rounded-full bg-brand-accent px-6 py-3 text-sm font-semibold text-slate-950"
          >
            Launch product demo
          </a>
          <a
            href="mailto:hello@landright.ai"
            className="rounded-full border border-slate-600 px-6 py-3 text-sm text-white"
          >
            Talk to our team
          </a>
        </div>
      </header>

      <section className="mx-auto mt-20 max-w-6xl grid gap-6 md:grid-cols-3">
        {highlights.map((item) => (
          <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h3 className="text-xl font-semibold text-white">{item.title}</h3>
            <p className="mt-3 text-sm text-slate-200">{item.body}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto mt-20 max-w-5xl rounded-3xl border border-white/10 bg-white/5 p-10 text-center">
        <p className="text-sm uppercase tracking-[0.4em] text-brand-accent">Trusted Pilots</p>
        <h2 className="mt-4 text-3xl font-semibold">Utility, pipeline, and fiber operators piloting 200–500 parcels.</h2>
        <p className="mt-4 text-slate-200">
          Success means zero missed statutory deadlines and complete binders for every filing.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-6 text-sm text-slate-400">
          {logos.map((logo) => (
            <span key={logo} className="rounded-full border border-white/10 px-4 py-2">
              {logo.replace("/logos/", "").replace(".svg", "").toUpperCase()}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
