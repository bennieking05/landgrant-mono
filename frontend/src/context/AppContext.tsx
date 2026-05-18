import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import {
  getPlatformProjects,
  listParcels,
  setApiAuth,
  type ParcelItem,
} from "@/lib/api";

export type Persona =
  | "landowner"
  | "land_agent"
  | "in_house_counsel"
  | "outside_counsel"
  | "firm_admin"
  | "admin";

type Project = {
  id: string;
  name: string;
};

type AppContextValue = {
  // Project selection
  projects: Project[];
  projectId: string;
  setProjectId: (id: string) => void;

  // Parcel selection
  parcels: ParcelItem[];
  parcelId: string | null;
  setParcelId: (id: string | null) => void;

  // Persona
  persona: Persona;
  setPersona: (p: Persona) => void;

  // Loading state
  loading: boolean;
  error: string | null;
  refreshParcels: () => void;
};

const AppContext = createContext<AppContextValue | null>(null);

// Dev fallback.  AppContext hydrates ``projects`` from
// ``GET /admin/platform/projects`` on mount; we only fall back to these
// sentinel rows when the request fails (e.g. offline dev) so the shell
// still renders a usable project picker.
const DEV_FALLBACK_PROJECTS: Project[] = [
  { id: "PRJ-001", name: "Highway 281 Expansion" },
  { id: "PRJ-002", name: "Pipeline Corridor Alpha" },
  { id: "PRJ-003", name: "Utility Easement Beta" },
];

type Props = {
  children: ReactNode;
};

const PERSONA_STORAGE_KEY = "landgrant.persona";
const VALID_PERSONAS: Persona[] = [
  "landowner",
  "land_agent",
  "in_house_counsel",
  "outside_counsel",
  "firm_admin",
  "admin",
];

function loadPersistedPersona(): Persona {
  if (typeof window === "undefined") return "land_agent";
  try {
    const saved = window.localStorage.getItem(PERSONA_STORAGE_KEY);
    if (saved && (VALID_PERSONAS as string[]).includes(saved)) {
      return saved as Persona;
    }
  } catch {
    // localStorage may be unavailable (e.g. privacy mode); fall through.
  }
  return "land_agent";
}

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

export function AppContextProvider({ children }: Props) {
  const [projectId, setProjectId] = useState(() => readQueryId("projectId") ?? "PRJ-001");
  const [parcelId, setParcelId] = useState<string | null>(() => readQueryId("parcelId"));
  const [persona, setPersona] = useState<Persona>(loadPersistedPersona);
  const [parcels, setParcels] = useState<ParcelItem[]>([]);
  const [projects, setProjects] = useState<Project[]>(DEV_FALLBACK_PROJECTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist persona so a page refresh or deep-link preserves the active role.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(PERSONA_STORAGE_KEY, persona);
    } catch {
      // Storage may be disabled; non-fatal.
    }
  }, [persona]);

  useEffect(() => {
    let cancelled = false;
    getPlatformProjects({ limit: 50 })
      .then((res) => {
        if (cancelled || !res?.projects?.length) return;
        setProjects(
          res.projects.map((p) => ({
            id: p.project_id,
            name: p.project_name,
          })),
        );
      })
      .catch(() => {
        // Keep the dev fallback if the admin endpoint is unreachable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshParcels = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await listParcels({ project_id: projectId });
      setParcels(res.items);

      if (res.items.length > 0) {
        const currentValid = res.items.some((p) => p.id === parcelId);
        if (!currentValid) {
          // Prefer a deep-linked parcel from the URL if it matches the fetched
          // list; otherwise fall back to the first available parcel so the
          // shell always has a selection.
          const queryParcel = readQueryId("parcelId");
          const deepLinked =
            queryParcel && res.items.some((p) => p.id === queryParcel)
              ? queryParcel
              : res.items[0].id;
          setParcelId(deepLinked);
        }
      } else {
        setParcelId(null);
      }
    } catch (e) {
      setError(String(e));
      setParcels([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Keep the shared API auth state in sync with the active persona so every
  // request carries the right X-Persona header (Phase 4.1).
  useEffect(() => {
    setApiAuth({ persona });
  }, [persona]);

  // Fetch parcels when project changes
  useEffect(() => {
    refreshParcels();
  }, [projectId]);

  const value: AppContextValue = {
    projects,
    projectId,
    setProjectId: (id: string) => {
      setProjectId(id);
      setParcelId(null); // Reset parcel when project changes
    },
    parcels,
    parcelId,
    setParcelId,
    persona,
    setPersona,
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
