import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import {
  getPlatformProjects,
  listParcels,
  type ParcelItem,
} from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export type Persona =
  | "landowner"
  | "land_agent"
  | "in_house_counsel"
  | "outside_counsel"
  | "firm_admin"
  | "platform_admin";

type Project = {
  id: string;
  name: string;
};

export type AppContextValue = {
  projects: Project[];
  projectId: string;
  setProjectId: (id: string) => void;

  parcels: ParcelItem[];
  parcelId: string | null;
  setParcelId: (id: string | null) => void;

  persona: Persona;

  loading: boolean;
  error: string | null;
  refreshParcels: () => void;
};

export const AppContext = createContext<AppContextValue | null>(null);

const DEV_FALLBACK_PROJECTS: Project[] = [];

type Props = {
  children: ReactNode;
};

function readQueryId(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    const params = new URLSearchParams(window.location.search);
    const v = params.get(key);
    return v && v.trim() ? v : null;
  } catch {
    return null;
  }
}

function normalizePersona(raw: string | undefined): Persona {
  if (!raw) return "land_agent";
  if (raw === "admin") return "platform_admin";
  return raw as Persona;
}

export function AppContextProvider({ children }: Props) {
  const { me } = useAuth();
  const persona = useMemo(() => normalizePersona(me?.persona), [me?.persona]);

  const [projectId, setProjectId] = useState(() => readQueryId("projectId") ?? "");
  const [parcelId, setParcelId] = useState<string | null>(() => readQueryId("parcelId"));
  const [parcels, setParcels] = useState<ParcelItem[]>([]);
  const [projects, setProjects] = useState<Project[]>(DEV_FALLBACK_PROJECTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadProjects() {
      if (!me) return;
      try {
        if (persona === "platform_admin") {
          const res = await getPlatformProjects({ limit: 50 });
          if (cancelled || !res?.projects?.length) return;
          const fetchedProjects = res.projects.map((p) => ({
            id: p.project_id,
            name: p.project_name,
          }));
          setProjects(fetchedProjects);
          setProjectId((current) => (current ? current : fetchedProjects[0]?.id ?? ""));
          return;
        }
        if (persona === "landowner") {
          setProjects([]);
          return;
        }
        const res = await listParcels({ limit: 300 });
        if (cancelled) return;
        const seen = new Map<string, string>();
        for (const p of res.items) {
          if (!seen.has(p.project_id)) seen.set(p.project_id, p.project_id);
        }
        const inferred = [...seen.keys()].map((id) => ({ id, name: id }));
        setProjects(inferred);
        setProjectId((current) => (current ? current : inferred[0]?.id ?? ""));
      } catch {
        if (!cancelled) setProjects([]);
      }
    }
    void loadProjects();
    return () => {
      cancelled = true;
    };
  }, [me, persona]);

  const refreshParcels = useCallback(async () => {
    if (!me) return;
    if (!projectId && persona !== "landowner") return;

    setLoading(true);
    setError(null);

    try {
      const res = await listParcels(
        persona === "landowner" ? { limit: 50 } : { project_id: projectId, limit: 200 },
      );
      setParcels(res.items);

      if (res.items.length > 0) {
        setParcelId((prev) => {
          const currentValid = res.items.some((p) => p.id === prev);
          if (currentValid) return prev;
          const queryParcel = readQueryId("parcelId");
          const deepLinked =
            queryParcel && res.items.some((p) => p.id === queryParcel)
              ? queryParcel
              : res.items[0].id;
          return deepLinked;
        });
      } else {
        setParcelId(null);
      }
    } catch (e) {
      setError(String(e));
      setParcels([]);
    } finally {
      setLoading(false);
    }
  }, [projectId, persona, me]);

  useEffect(() => {
    void refreshParcels();
  }, [refreshParcels]);

  const value: AppContextValue = {
    projects,
    projectId,
    setProjectId: (id: string) => {
      setProjectId(id);
      setParcelId(null);
    },
    parcels,
    parcelId,
    setParcelId,
    persona,
    loading,
    error,
    refreshParcels,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within AppContextProvider");
  }
  return context;
}
