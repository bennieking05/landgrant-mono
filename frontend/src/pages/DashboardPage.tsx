import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RTooltip,
  Cell,
  CartesianGrid,
} from "recharts";
import {
  LayoutGrid,
  CalendarClock,
  AlertTriangle,
  FolderOpen,
  Scale,
  CheckCircle2,
  ListTodo,
  ClipboardList,
} from "lucide-react";
import { useAppContext, type Persona } from "@/context";
import { navForPersona } from "@/constants/navConfig";
import {
  Card,
  CardBody,
  StageBadge,
  RiskBadge,
  EmptyState,
  Skeleton,
  Button,
  LegalDisclaimer,
} from "@/components/ui";
import { STAGE_ORDER, STAGE_COLORS, stageLabel } from "@/components/ui";
import { formatDate, daysUntil } from "@/lib/format";
import { addDays, formatISO } from "date-fns";
import { getDashboardHome, type DashboardHomeResponse } from "@/lib/api";

type KpiDef = {
  icon: typeof LayoutGrid;
  label: string;
  value: number;
  tone: "brand" | "warning" | "danger" | "info" | "success";
  to?: string;
};

const TONE_CLASS: Record<KpiDef["tone"], string> = {
  brand: "bg-brand/10 text-brand",
  warning: "bg-warning-bg text-warning-fg",
  danger: "bg-danger-bg text-danger-fg",
  info: "bg-info-bg text-info-fg",
  success: "bg-success-bg text-success-fg",
};

function KpiCard({ def }: { def: KpiDef }) {
  const Icon = def.icon;
  const inner = (
    <CardBody className="flex items-center gap-3">
      <span className={`flex h-10 w-10 items-center justify-center rounded-control ${TONE_CLASS[def.tone]}`}>
        <Icon className="h-5 w-5" />
      </span>
      <div>
        <p className="text-caption font-medium uppercase text-slate-500">{def.label}</p>
        <p className="text-h1 tabular-nums text-slate-900">{def.value}</p>
      </div>
    </CardBody>
  );
  return def.to ? (
    <Card className="transition hover:border-brand">
      <Link to={def.to} className="block">
        {inner}
      </Link>
    </Card>
  ) : (
    <Card>{inner}</Card>
  );
}

const PERSONA_HEADLINE: Record<Persona, { title: string; subtitle: string }> = {
  landowner: { title: "Your parcel", subtitle: "" },
  land_agent: { title: "Land agent dashboard", subtitle: "Parcels, deadlines, and risk across your assignments." },
  in_house_counsel: { title: "Counsel dashboard", subtitle: "Approvals, litigation exposure, and statutory deadlines." },
  outside_counsel: { title: "Counsel dashboard", subtitle: "Approvals, litigation exposure, and statutory deadlines." },
  firm_admin: { title: "Executive dashboard", subtitle: "Portfolio health across projects and stages." },
  platform_admin: { title: "Executive dashboard", subtitle: "Portfolio health across projects and stages." },
};

export function DashboardPage() {
  const { persona, parcels, loading, projectId } = useAppContext();
  const [dash, setDash] = useState<DashboardHomeResponse | null>(null);

  useEffect(() => {
    if (persona === "landowner") {
      setDash(null);
      return;
    }
    let cancelled = false;
    void getDashboardHome(projectId || undefined)
      .then((d) => {
        if (!cancelled) setDash(d);
      })
      .catch(() => {
        if (!cancelled) setDash(null);
      });
    return () => {
      cancelled = true;
    };
  }, [persona, projectId]);

  const stats = useMemo(() => {
    const byStage = new Map<string, number>();
    let upcoming = 0;
    let highRisk = 0;
    const sourceStages = dash?.parcels_by_stage;
    if (sourceStages && Object.keys(sourceStages).length > 0) {
      for (const [k, v] of Object.entries(sourceStages)) {
        byStage.set(k, v);
      }
    } else {
      for (const p of parcels) {
        byStage.set(p.stage, (byStage.get(p.stage) ?? 0) + 1);
      }
    }
    for (const p of parcels) {
      const d = daysUntil(p.next_deadline_at);
      if (d !== null && d >= 0 && d <= 14) upcoming += 1;
      if (p.risk_score >= 70) highRisk += 1;
    }
    const total = dash?.sample_size ?? parcels.length;
    const upcomingCount = dash?.deadlines_next_14_count ?? upcoming;
    return { byStage, upcoming: upcomingCount, highRisk, total };
  }, [parcels, dash]);

  const isCounsel = persona === "in_house_counsel" || persona === "outside_counsel";
  const isExec = persona === "firm_admin" || persona === "platform_admin";

  const deadlineBeforeIso = formatISO(addDays(new Date(), 14));
  const workbenchDeadlineLink = `/workbench?deadline_before=${encodeURIComponent(deadlineBeforeIso)}${
    projectId ? `&projectId=${encodeURIComponent(projectId)}` : ""
  }`;

  const kpis = useMemo<KpiDef[]>(() => {
    const base: KpiDef[] = [
      { icon: LayoutGrid, label: "Parcels", value: stats.total, tone: "brand", to: "/workbench" },
      {
        icon: CalendarClock,
        label: "Deadlines <= 14 days",
        value: stats.upcoming,
        tone: "warning",
        to: workbenchDeadlineLink,
      },
      { icon: AlertTriangle, label: "High risk", value: stats.highRisk, tone: "danger", to: "/workbench?minRisk=70" },
    ];
    if (isCounsel) {
      base.push({
        icon: Scale,
        label: "In litigation",
        value: stats.byStage.get("litigation") ?? 0,
        tone: "danger",
        to: "/workbench?stage=litigation",
      });
    } else if (isExec) {
      base.push({
        icon: CheckCircle2,
        label: "Closed",
        value: stats.byStage.get("closed") ?? 0,
        tone: "success",
        to: "/workbench?stage=closed",
      });
    } else {
      base.push({
        icon: FolderOpen,
        label: "Active stages",
        value: stats.byStage.size,
        tone: "info",
      });
    }
    if (dash && !isCounsel && !isExec) {
      base.splice(
        1,
        0,
        {
          icon: CheckCircle2,
          label: "Offers awaiting response",
          value: dash.pending_offers_count,
          tone: "warning",
          to: "/workbench",
        },
        {
          icon: ListTodo,
          label: "Overdue follow-ups",
          value: dash.overdue_tasks_count,
          tone: "danger",
          to: "/workbench",
        },
      );
    }
    if (dash != null && typeof dash.pending_approvals_count === "number" && isCounsel) {
      base.push({
        icon: ClipboardList,
        label: "Approvals pending",
        value: dash.pending_approvals_count,
        tone: "brand",
        to: "/counsel",
      });
    }
    return base;
  }, [stats, dash, isCounsel, isExec, workbenchDeadlineLink]);

  const chartData = useMemo(
    () =>
      STAGE_ORDER.filter((s) => stats.byStage.has(s)).map((s) => ({
        stage: s,
        label: stageLabel(s),
        count: stats.byStage.get(s) ?? 0,
      })),
    [stats.byStage],
  );

  const soonest = useMemo(
    () =>
      [...parcels]
        .filter((p) => p.next_deadline_at)
        .sort(
          (a, b) =>
            new Date(a.next_deadline_at!).getTime() - new Date(b.next_deadline_at!).getTime(),
        )
        .slice(0, 6),
    [parcels],
  );

  const quickLinks = navForPersona(persona).filter(
    (i) => i.section === "workspace" && i.path !== "/",
  );

  const headline = PERSONA_HEADLINE[persona];

  if (loading && parcels.length === 0) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-slate-900">{headline.title}</h1>
        <p className="mt-1 text-small text-slate-600">
          {headline.subtitle || `What needs your attention across ${projectId ? "this project" : "your portfolio"}.`}
        </p>
      </div>

      {parcels.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState
              icon={FolderOpen}
              title="No parcels yet"
              message="Create a parcel case from intake, or import parcels via CSV to populate your dashboard."
            />
            <div className="mt-2 flex justify-center">
              <Button asChild>
                <Link to="/workbench">Go to workbench</Link>
              </Button>
            </div>
          </CardBody>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {kpis.map((k) => (
              <KpiCard key={k.label} def={k} />
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardBody>
                <h2 className="text-h3 text-slate-900">Parcels by stage</h2>
                {stats.total < 3 ? (
                  <p className="mt-2 text-caption text-slate-400">
                    Limited data - showing all {stats.total} parcel{stats.total === 1 ? "" : "s"}.
                  </p>
                ) : null}
                <div className="mt-4 h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                      <CartesianGrid horizontal={false} stroke="#e2e8f0" />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tick={{ fill: "#64748b", fontSize: 12 }}
                        stroke="#cbd5e1"
                      />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={96}
                        tick={{ fill: "#475569", fontSize: 12 }}
                        stroke="#cbd5e1"
                      />
                      <RTooltip
                        cursor={{ fill: "#f1f5f9" }}
                        contentStyle={{
                          borderRadius: 8,
                          border: "1px solid #e2e8f0",
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Parcels">
                        {chartData.map((d) => (
                          <Cell key={d.stage} fill={STAGE_COLORS[d.stage] ?? "#64748b"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <h2 className="text-h3 text-slate-900">Upcoming deadlines</h2>
                {soonest.length === 0 ? (
                  <p className="mt-4 text-small text-slate-500">No scheduled deadlines.</p>
                ) : (
                  <ul className="mt-4 divide-y divide-slate-100">
                    {soonest.map((p) => {
                      const d = daysUntil(p.next_deadline_at);
                      const overdue = d !== null && d < 0;
                      const soon = d !== null && d >= 0 && d <= 7;
                      return (
                        <li key={p.id} className="flex items-center justify-between gap-3 py-2">
                          <Link
                            to={`/parcels/${encodeURIComponent(p.id)}?projectId=${encodeURIComponent(p.project_id)}`}
                            className="font-id text-small text-brand hover:underline"
                          >
                            {p.id}
                          </Link>
                          <StageBadge stage={p.stage} />
                          <span
                            className={
                              overdue
                                ? "text-small font-medium text-danger"
                                : soon
                                  ? "text-small font-medium text-warning-fg"
                                  : "text-small text-slate-600"
                            }
                          >
                            {formatDate(p.next_deadline_at)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardBody>
            </Card>
          </div>

          <div>
            <h2 className="mb-3 text-h3 text-slate-900">Recent parcels</h2>
            <Card>
              <CardBody className="p-0">
                <ul className="divide-y divide-slate-100">
                  {parcels.slice(0, 8).map((p) => (
                    <li key={p.id}>
                      <Link
                        to={`/parcels/${encodeURIComponent(p.id)}?projectId=${encodeURIComponent(p.project_id)}`}
                        className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-slate-50"
                      >
                        <span className="font-id text-small text-slate-900">{p.id}</span>
                        <StageBadge stage={p.stage} />
                        <RiskBadge score={p.risk_score} />
                        <span className="hidden text-small text-slate-500 sm:block">
                          {p.next_deadline_at ? formatDate(p.next_deadline_at) : "No deadline"}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          </div>
        </>
      )}

      {quickLinks.length > 0 && (
        <div>
          <h2 className="mb-3 text-h3 text-slate-900">Jump to</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {quickLinks.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className="flex items-center gap-3 rounded-card border border-slate-200 bg-white p-4 shadow-card transition hover:border-brand"
                >
                  <Icon className="h-5 w-5 text-brand" />
                  <span className="text-small font-medium text-slate-800">{item.fallbackLabel}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      <LegalDisclaimer />
    </div>
  );
}
