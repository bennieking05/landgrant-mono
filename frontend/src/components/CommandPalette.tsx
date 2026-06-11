import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import { Search, CornerDownLeft } from "lucide-react";
import { useAppContext } from "@/context";
import { navForPersona } from "@/constants/navConfig";
import { globalSearch, type SearchResult } from "@/lib/api";
import { stageLabel } from "@/components/ui";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/**
 * Cmd-K global search (UX-2): navigate by identifier - parcel number, project,
 * owner, cause number. Admin personas hit the server search endpoint; everyone
 * gets fast client-side jumps over loaded parcels + role navigation.
 */
export function CommandPalette({ open, onOpenChange }: Props) {
  const navigate = useNavigate();
  const { persona, parcels, projects } = useAppContext();
  const [query, setQuery] = useState("");
  const [remote, setRemote] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  const canRemoteSearch = persona === "platform_admin";

  useEffect(() => {
    if (!open) {
      setQuery("");
      setRemote([]);
    }
  }, [open]);

  useEffect(() => {
    if (!canRemoteSearch || query.trim().length < 2) {
      setRemote([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    const id = window.setTimeout(async () => {
      try {
        const res = await globalSearch(query.trim(), 8);
        if (!cancelled) setRemote(res.results);
      } catch {
        if (!cancelled) setRemote([]);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [query, canRemoteSearch]);

  function go(to: string) {
    onOpenChange(false);
    navigate(to);
  }

  const navItems = navForPersona(persona);

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label="Global search"
      className="fixed left-1/2 top-[12vh] z-[110] w-[92vw] max-w-xl -translate-x-1/2 overflow-hidden rounded-modal border border-slate-200 bg-white shadow-overlay"
    >
      <div className="flex items-center gap-2 border-b border-slate-200 px-4">
        <Search className="h-4 w-4 text-slate-400" aria-hidden />
        <Command.Input
          value={query}
          onValueChange={setQuery}
          placeholder="Search parcels, projects, owners, cause numbers..."
          className="h-12 w-full bg-transparent text-body text-slate-900 outline-none placeholder:text-slate-400"
        />
        <kbd className="hidden rounded bg-slate-100 px-1.5 py-0.5 text-caption text-slate-500 sm:block">
          Esc
        </kbd>
      </div>
      <Command.List className="max-h-[60vh] overflow-y-auto p-2">
        <Command.Empty className="px-3 py-6 text-center text-small text-slate-500">
          {searching ? "Searching..." : "No matches."}
        </Command.Empty>

        <Command.Group heading="Go to" className="px-1 text-caption font-medium text-slate-500">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Command.Item
                key={item.path}
                value={`nav ${item.fallbackLabel}`}
                onSelect={() => go(item.path)}
                className="flex cursor-pointer items-center gap-2 rounded-control px-3 py-2 text-small text-slate-700 data-[selected=true]:bg-slate-100"
              >
                <Icon className="h-4 w-4 text-slate-400" />
                {item.fallbackLabel}
              </Command.Item>
            );
          })}
        </Command.Group>

        {parcels.length > 0 ? (
          <Command.Group heading="Parcels" className="px-1 text-caption font-medium text-slate-500">
            {parcels.slice(0, 12).map((p) => (
              <Command.Item
                key={p.id}
                value={`parcel ${p.id} ${p.stage}`}
                onSelect={() =>
                  go(`/parcels/${encodeURIComponent(p.id)}?projectId=${encodeURIComponent(p.project_id)}`)
                }
                className="flex cursor-pointer items-center justify-between gap-2 rounded-control px-3 py-2 text-small text-slate-700 data-[selected=true]:bg-slate-100"
              >
                <span className="font-id">{p.id}</span>
                <span className="text-caption text-slate-400">{stageLabel(p.stage)}</span>
              </Command.Item>
            ))}
          </Command.Group>
        ) : null}

        {projects.length > 0 ? (
          <Command.Group heading="Projects" className="px-1 text-caption font-medium text-slate-500">
            {projects.slice(0, 8).map((proj) => (
              <Command.Item
                key={proj.id}
                value={`project ${proj.name} ${proj.id}`}
                onSelect={() => go(`/workbench?projectId=${encodeURIComponent(proj.id)}`)}
                className="flex cursor-pointer items-center gap-2 rounded-control px-3 py-2 text-small text-slate-700 data-[selected=true]:bg-slate-100"
              >
                {proj.name}
              </Command.Item>
            ))}
          </Command.Group>
        ) : null}

        {remote.length > 0 ? (
          <Command.Group heading="Search results" className="px-1 text-caption font-medium text-slate-500">
            {remote.map((r) => (
              <Command.Item
                key={`${r.result_type}-${r.id}`}
                value={`result ${r.title} ${r.subtitle ?? ""}`}
                onSelect={() => {
                  if (r.parcel_id) {
                    const proj = r.project_id ? `?projectId=${encodeURIComponent(r.project_id)}` : "";
                    go(`/parcels/${encodeURIComponent(r.parcel_id)}${proj}`);
                  } else if (r.project_id) {
                    go(`/workbench?projectId=${encodeURIComponent(r.project_id)}`);
                  } else {
                    go("/admin");
                  }
                }}
                className="flex cursor-pointer items-center justify-between gap-2 rounded-control px-3 py-2 text-small text-slate-700 data-[selected=true]:bg-slate-100"
              >
                <span className="min-w-0 truncate">
                  <span className="font-medium">{r.title}</span>
                  {r.subtitle ? <span className="ml-2 text-slate-400">{r.subtitle}</span> : null}
                </span>
                <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-caption text-slate-500">
                  {r.result_type}
                </span>
              </Command.Item>
            ))}
          </Command.Group>
        ) : null}
      </Command.List>
      <div className="flex items-center justify-end gap-1 border-t border-slate-200 px-4 py-2 text-caption text-slate-400">
        <CornerDownLeft className="h-3 w-3" /> to open
      </div>
    </Command.Dialog>
  );
}
