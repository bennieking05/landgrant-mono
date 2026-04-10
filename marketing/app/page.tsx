const highlights: { title: string; body?: string }[] = [
  {
    title: "Workflow + audit trails",
    body: "Designed for regulated infrastructure projects.",
  },
  {
    title: "Counsel-in-the-loop review and approvals",
  },
  {
    title: "Configurable rules engine",
    body: "Texas and Indiana at launch (more states to follow).",
  },
];

const pilots = [
  { src: "/logos/utility.svg", label: "Utility" },
  { src: "/logos/pipeline.svg", label: "Pipeline" },
  { src: "/logos/fiber.svg", label: "Fiber" },
];

export default function MarketingPage() {
  return (
    <div className="flex flex-1 flex-col bg-gradient-to-b from-slate-50 via-white to-slate-100 px-6 py-12 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 sm:py-16">
      <header className="mx-auto max-w-5xl text-center">
        <p className="text-sm uppercase tracking-[0.3em] text-brand-accent">LandGrantIQ</p>
        <h1 className="mt-6 text-4xl font-semibold leading-tight text-slate-900 sm:text-5xl dark:text-white">
          LandGrantIQ is building the operating system for{" "}
          <span className="text-brand-accent">Right-of-Way</span>.
        </h1>
        <p className="mt-6 text-lg text-slate-600 dark:text-slate-200">
          We&apos;re developing an AI-assisted workflow platform for easements, ROW, and eminent domain,
          combining project execution, deadline tracking, and counsel-ready documentation in one place.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <a
            href="mailto:hello@landgrant.ai?subject=LandGrantIQ%20early%20access"
            className="rounded-full bg-brand-accent px-6 py-3 text-sm font-semibold text-slate-950 shadow-sm transition hover:opacity-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0F3D7A]"
          >
            Request early access
          </a>
          <a
            href="mailto:hello@landgrant.ai?subject=LandGrantIQ%20-%20Talk%20to%20the%20team"
            className="rounded-full border border-slate-300 px-6 py-3 text-sm font-medium text-slate-800 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0F3D7A] dark:border-slate-600 dark:text-white dark:hover:bg-white/10"
          >
            Talk to the team
          </a>
        </div>
      </header>

      <section className="mx-auto mt-16 max-w-6xl grid gap-6 sm:mt-20 md:grid-cols-3" aria-labelledby="highlights-heading">
        <h2 id="highlights-heading" className="sr-only">
          Product highlights
        </h2>
        {highlights.map((item) => (
          <div
            key={item.title}
            className="rounded-2xl border border-slate-200/90 bg-white/80 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/5"
          >
            <h3 className="text-xl font-semibold text-slate-900 dark:text-white">{item.title}</h3>
            {item.body ? (
              <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-200">{item.body}</p>
            ) : null}
          </div>
        ))}
      </section>

      <section className="mx-auto mt-16 max-w-5xl rounded-3xl border border-slate-200/90 bg-white/80 p-8 text-center shadow-sm dark:border-white/10 dark:bg-white/5 sm:mt-20 sm:p-10">
        <p className="text-sm uppercase tracking-[0.4em] text-brand-accent">Trusted Pilots</p>
        <h2 className="mt-4 text-2xl font-semibold text-slate-900 sm:text-3xl dark:text-white">
          Utility, pipeline, and fiber operators piloting 200–500 parcels.
        </h2>
        <p className="mt-4 text-slate-600 dark:text-slate-200">
          Success means zero missed statutory deadlines and complete binders for every filing.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-8">
          {pilots.map((p) => (
            <div
              key={p.src}
              className="flex flex-col items-center gap-2 rounded-2xl border border-slate-200/90 px-6 py-4 text-slate-700 dark:border-white/10 dark:text-slate-200"
            >
              <img src={p.src} alt="" width={120} height={40} className="h-10 w-auto opacity-90 dark:opacity-100" />
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                {p.label}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
