import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  MessageSquare,
  Gavel,
  CalendarClock,
  Info,
  RefreshCw,
} from "lucide-react";
import {
  listParcels,
  listOffers,
  listCommunications,
  listRuleResults,
  listDeadlines,
  getProjectHierarchy,
  type ParcelItem,
  type OfferItem,
  type CommItem,
  type RuleResultItem,
  type DeadlineItem,
  type ProjectHierarchyResponse,
} from "@/lib/api";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useAppContext } from "@/context";
import { formatDate, formatDateTime, formatRelative, formatCurrency } from "@/lib/format";
import {
  Card,
  CardBody,
  StageBadge,
  StageLegend,
  RiskBadge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Tooltip,
  Skeleton,
  SkeletonText,
  Alert,
  Badge,
  Button,
  EmptyState,
  Breadcrumbs,
  type Crumb,
} from "@/components/ui";
import { TitlePanel } from "@/components/TitlePanel";
import { AppraisalPanel } from "@/components/AppraisalPanel";
import { DocumentExtraction } from "@/components/DocumentExtraction";
import { LitigationPanel } from "@/components/LitigationPanel";
import { AIAuditDrawer } from "@/components/AIAuditDrawer";

type TimelineEvent = {
  id: string;
  kind: "offer" | "communication" | "rule" | "deadline";
  title: string;
  detail?: string;
  at: string | null;
};

const KIND_ICON = {
  offer: FileText,
  communication: MessageSquare,
  rule: Gavel,
  deadline: CalendarClock,
} as const;

const KIND_TONE: Record<TimelineEvent["kind"], string> = {
  offer: "bg-accent-50 text-accent-700",
  communication: "bg-info-bg text-info-fg",
  rule: "bg-stage-litigation-bg text-stage-litigation-fg",
  deadline: "bg-warning-bg text-warning-fg",
};

export function ParcelDetailPage() {
  const { parcelId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const projectIdParam = searchParams.get("projectId") ?? undefined;
  const { projects } = useAppContext();

  useDocumentTitle(parcelId, "Parcel");

  const [parcel, setParcel] = useState<ParcelItem | null>(null);
  const [hierarchy, setHierarchy] = useState<ProjectHierarchyResponse | null>(null);
  const [offers, setOffers] = useState<OfferItem[]>([]);
  const [comms, setComms] = useState<CommItem[]>([]);
  const [rules, setRules] = useState<RuleResultItem[]>([]);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [auditOpen, setAuditOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    // Hard error timeout (UX-11): never hang forever on a stalled request.
    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        setError("This is taking longer than expected. The server may be slow or unreachable.");
        setLoading(false);
      }
    }, 10_000);

    (async () => {
      try {
        const list = await listParcels({
          q: parcelId,
          project_id: projectIdParam,
          limit: 50,
        });
        const found = list.items.find((p) => p.id === parcelId) ?? null;
        if (cancelled) return;
        setParcel(found);

        const projectId = found?.project_id ?? projectIdParam;
        const [offersRes, commsRes, rulesRes, deadlinesRes] = await Promise.allSettled([
          listOffers(parcelId),
          listCommunications(parcelId),
          listRuleResults(parcelId),
          projectId ? listDeadlines(projectId) : Promise.resolve({ items: [] as DeadlineItem[] }),
        ]);
        if (cancelled) return;
        if (offersRes.status === "fulfilled") setOffers(offersRes.value.items ?? []);
        if (commsRes.status === "fulfilled") setComms(commsRes.value.items ?? []);
        if (rulesRes.status === "fulfilled") setRules(rulesRes.value.items ?? []);
        if (deadlinesRes.status === "fulfilled") {
          const items = (deadlinesRes.value as { items: DeadlineItem[] }).items ?? [];
          setDeadlines(items.filter((d) => !d.parcel_id || d.parcel_id === parcelId));
        }
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) {
          window.clearTimeout(timeout);
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [parcelId, projectIdParam, reloadKey]);

  const timeline = useMemo<TimelineEvent[]>(() => {
    const events: TimelineEvent[] = [];
    for (const o of offers) {
      events.push({
        id: `offer-${o.id}`,
        kind: "offer",
        title: `Offer${o.offer_number ? ` #${o.offer_number}` : ""}${o.offer_type ? ` - ${o.offer_type}` : ""}`,
        detail: [o.amount != null ? formatCurrency(o.amount) : null, o.status]
          .filter(Boolean)
          .join(" - "),
        at: o.sent_date ?? o.created_date ?? null,
      });
    }
    for (const c of comms) {
      events.push({
        id: `comm-${c.id}`,
        kind: "communication",
        title: `${c.channel} communication`,
        detail: [c.summary, c.status].filter(Boolean).join(" - "),
        at: c.ts ?? null,
      });
    }
    for (const r of rules.filter((x) => x.fired)) {
      events.push({
        id: `rule-${r.id}`,
        kind: "rule",
        title: `Rule fired: ${r.rule_id}`,
        detail: r.citation,
        at: r.fired_at ?? null,
      });
    }
    for (const d of deadlines) {
      events.push({
        id: `deadline-${d.id}`,
        kind: "deadline",
        title: `Deadline: ${d.title}`,
        detail: d.citation ?? d.deadline_type ?? undefined,
        at: d.due_at ?? null,
      });
    }
    return events.sort((a, b) => {
      const ta = a.at ? new Date(a.at).getTime() : 0;
      const tb = b.at ? new Date(b.at).getTime() : 0;
      return tb - ta;
    });
  }, [offers, comms, rules, deadlines]);

  useEffect(() => {
    const pid = parcel?.project_id;
    if (!pid) {
      setHierarchy(null);
      return;
    }
    let cancelled = false;
    void getProjectHierarchy(pid)
      .then((h) => {
        if (!cancelled) setHierarchy(h);
      })
      .catch(() => {
        if (!cancelled) setHierarchy(null);
      });
    return () => {
      cancelled = true;
    };
  }, [parcel?.project_id, reloadKey]);

  const breadcrumbItems = useMemo((): Crumb[] => {
    if (!parcel) return [];
    const items: Crumb[] = [];
    const proj = projects.find((p) => p.id === parcel.project_id);
    const pname = proj?.name ?? hierarchy?.project.name ?? parcel.project_id;
    items.push({
      label: pname,
      to: `/workbench?projectId=${encodeURIComponent(parcel.project_id)}`,
    });
    let alignLabel: string | undefined;
    let segLabel: string | undefined;
    if (hierarchy) {
      for (const al of hierarchy.alignments) {
        for (const seg of al.segments) {
          if (seg.parcels.some((p) => p.id === parcel.id)) {
            alignLabel = al.name;
            segLabel =
              seg.name ??
              (seg.segment_number != null ? `Segment ${seg.segment_number}` : seg.id);
            break;
          }
        }
        if (alignLabel) break;
      }
      if (!alignLabel && hierarchy.unassigned_parcels.some((p) => p.id === parcel.id)) {
        segLabel = "Unassigned route segment";
      }
    }
    if (alignLabel) items.push({ label: alignLabel });
    if (segLabel) items.push({ label: segLabel });
    items.push({ label: `Parcel ${parcel.id}` });
    return items;
  }, [parcel, projects, hierarchy]);

  if (loading && !parcel) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full" />
        <SkeletonText lines={6} />
      </div>
    );
  }

  if (error && !parcel) {
    return (
      <div className="space-y-4">
        <BackLink projectId={projectIdParam} />
        <Alert variant="danger" title="Could not load parcel" action={{ label: "Retry", onClick: () => setReloadKey((k) => k + 1) }}>
          {error}
        </Alert>
      </div>
    );
  }

  if (!parcel) {
    return (
      <div className="space-y-4">
        <BackLink projectId={projectIdParam} />
        <Card>
          <CardBody>
            <EmptyState title="Parcel not found" message={`No parcel matches "${parcelId}", or you don't have access to it.`} />
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <BackLink projectId={parcel.project_id} />
      {breadcrumbItems.length > 0 ? <Breadcrumbs items={breadcrumbItems} className="pb-2" /> : null}

      {/* Persistent header */}
      <Card>
        <CardBody className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="font-id text-h1 text-slate-900">{parcel.id}</h1>
              <Tooltip content={<StageLegend className="w-48" />}>
                <span>
                  <StageBadge stage={parcel.stage} />
                </span>
              </Tooltip>
              <RiskBadge score={parcel.risk_score} />
            </div>
            <dl className="flex flex-wrap gap-x-6 gap-y-1 text-small text-slate-600">
              <div className="flex gap-1">
                <dt className="text-slate-500">Owner:</dt>
                <dd>{parcel.owner ?? "-"}</dd>
              </div>
              <div className="flex gap-1">
                <dt className="text-slate-500">County:</dt>
                <dd>
                  {parcel.county ?? "-"}
                  {parcel.parcel_state ? `, ${parcel.parcel_state}` : ""}
                </dd>
              </div>
              <div className="flex gap-1">
                <dt className="text-slate-500">Assigned agent:</dt>
                <dd>{parcel.assignee_name ?? "Unassigned"}</dd>
              </div>
              <div className="flex gap-1">
                <dt className="text-slate-500">Next deadline:</dt>
                <dd>{parcel.next_deadline_at ? formatDate(parcel.next_deadline_at) : "None"}</dd>
              </div>
            </dl>
          </div>
          <div className="flex items-center gap-3">
            {parcel.updated_at ? (
              <span className="flex items-center gap-1 text-caption text-slate-500" title={formatDateTime(parcel.updated_at)}>
                <Info className="h-3.5 w-3.5" /> Updated {formatRelative(parcel.updated_at)}
              </span>
            ) : null}
            <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </div>
        </CardBody>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="offers">Offers ({offers.length})</TabsTrigger>
          <TabsTrigger value="title">Title &amp; curative</TabsTrigger>
          <TabsTrigger value="appraisals">Appraisals</TabsTrigger>
          <TabsTrigger value="communications">Communications ({comms.length})</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="deadlines">Deadlines ({deadlines.length})</TabsTrigger>
          <TabsTrigger value="litigation">Litigation</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="pt-4">
          <Card>
            <CardBody>
              <h2 className="text-h3 text-slate-900">Event timeline</h2>
              <p className="mt-0.5 text-caption text-slate-500">
                Offers, communications, notices, rule firings, and deadlines for this parcel.
              </p>
              {timeline.length === 0 ? (
                <p className="mt-6 text-small text-slate-500">No recorded activity yet.</p>
              ) : (
                <ol className="mt-4 space-y-0">
                  {timeline.map((ev, i) => {
                    const Icon = KIND_ICON[ev.kind];
                    return (
                      <li key={ev.id} className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <span className={`flex h-8 w-8 items-center justify-center rounded-full ${KIND_TONE[ev.kind]}`}>
                            <Icon className="h-4 w-4" />
                          </span>
                          {i < timeline.length - 1 ? <span className="w-px flex-1 bg-slate-200" /> : null}
                        </div>
                        <div className="pb-5">
                          <p className="text-small font-medium text-slate-900">{ev.title}</p>
                          {ev.detail ? <p className="text-small text-slate-600">{ev.detail}</p> : null}
                          <p className="text-caption text-slate-500">
                            {ev.at ? `${formatDate(ev.at)} - ${formatRelative(ev.at)}` : "Date unknown"}
                          </p>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              )}
            </CardBody>
          </Card>
        </TabsContent>

        <TabsContent value="offers" className="pt-4">
          <Card>
            <CardBody>
              {offers.length === 0 ? (
                <EmptyState title="No offers" message="No offers have been recorded for this parcel." />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {offers.map((o) => (
                    <li key={o.id} className="flex items-center justify-between gap-3 py-3">
                      <span className="text-small font-medium text-slate-900">
                        Offer{o.offer_number ? ` #${o.offer_number}` : ""} {o.offer_type ?? ""}
                      </span>
                      <span className="text-small tabular-nums text-slate-700">
                        {o.amount != null ? formatCurrency(o.amount) : "-"}
                      </span>
                      <Badge variant="neutral">{o.status ?? "unknown"}</Badge>
                      <span className="text-caption text-slate-500">
                        {o.sent_date ? formatDate(o.sent_date) : o.created_date ? formatDate(o.created_date) : "-"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </TabsContent>

        <TabsContent value="title" className="pt-4">
          <TitlePanel parcelId={parcel.id} />
        </TabsContent>

        <TabsContent value="appraisals" className="pt-4">
          <AppraisalPanel parcelId={parcel.id} />
        </TabsContent>

        <TabsContent value="communications" className="pt-4">
          <Card>
            <CardBody>
              {comms.length === 0 ? (
                <EmptyState title="No communications" message="No communications logged for this parcel." />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {comms.map((c) => (
                    <li key={c.id} className="flex items-center justify-between gap-3 py-3">
                      <span className="text-small text-slate-700">{c.summary ?? c.channel}</span>
                      <Badge variant="info">{c.channel}</Badge>
                      <span className="text-caption text-slate-500">{c.ts ? formatDate(c.ts) : "-"}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </TabsContent>

        <TabsContent value="documents" className="pt-4">
          <DocumentExtraction parcelId={parcel.id} />
        </TabsContent>

        <TabsContent value="deadlines" className="pt-4">
          <Card>
            <CardBody>
              {deadlines.length === 0 ? (
                <EmptyState title="No deadlines" message="No deadlines scheduled for this parcel." />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {deadlines.map((d) => (
                    <li key={d.id} className="flex items-center justify-between gap-3 py-3">
                      <span className="text-small text-slate-700">{d.title}</span>
                      {d.citation ? <span className="font-id text-caption text-slate-500">{d.citation}</span> : null}
                      <span className="text-small font-medium text-slate-700">{formatDate(d.due_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </TabsContent>

        <TabsContent value="litigation" className="pt-4">
          <LitigationPanel parcelId={parcel.id} projectId={parcel.project_id} />
        </TabsContent>

        <TabsContent value="audit" className="pt-4">
          <Card>
            <CardBody className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-h3 text-slate-900">AI audit trail</h2>
                <p className="mt-0.5 text-caption text-slate-500">
                  Model runs, prompt versions, citations, and escalations recorded for this parcel.
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setAuditOpen(true)}>
                View AI audit
              </Button>
            </CardBody>
          </Card>
        </TabsContent>
      </Tabs>

      <AIAuditDrawer
        open={auditOpen}
        onClose={() => setAuditOpen(false)}
        resourceId={parcel.id}
        title={`AI audit · ${parcel.id}`}
      />
    </div>
  );
}

function BackLink({ projectId }: { projectId?: string }) {
  return (
    <Link
      to={projectId ? `/workbench?projectId=${encodeURIComponent(projectId)}` : "/"}
      className="inline-flex items-center gap-1.5 text-small text-slate-500 hover:text-slate-900"
    >
      <ArrowLeft className="h-4 w-4" /> Back to parcels
    </Link>
  );
}
