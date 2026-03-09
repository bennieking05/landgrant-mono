"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { listParcels, type ParcelItem } from "@/lib/api";

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

  // Loading state
  loading: boolean;
  error: string | null;
  refreshParcels: () => void;
};

const AppContext = createContext<AppContextValue | null>(null);

// Demo projects - in production, these would come from an API
const DEMO_PROJECTS: Project[] = [
  { id: "PRJ-001", name: "Highway 281 Expansion" },
  { id: "PRJ-002", name: "Pipeline Corridor Alpha" },
  { id: "PRJ-003", name: "Utility Easement Beta" },
];

type Props = {
  children: ReactNode;
};

export function AppContextProvider({ children }: Props) {
  const [projectId, setProjectId] = useState("PRJ-001");
  const [parcelId, setParcelId] = useState<string | null>(null);
  const [parcels, setParcels] = useState<ParcelItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshParcels = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await listParcels({ project_id: projectId });
      setParcels(res.items);

      // Auto-select first parcel if none selected or current selection not in list
      if (res.items.length > 0) {
        const currentValid = res.items.some((p) => p.id === parcelId);
        if (!currentValid) {
          setParcelId(res.items[0].id);
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
  }, [projectId, parcelId]);

  // Fetch parcels when project changes
  useEffect(() => {
    refreshParcels();
  }, [projectId]);

  const value: AppContextValue = {
    projects: DEMO_PROJECTS,
    projectId,
    setProjectId: (id: string) => {
      setProjectId(id);
      setParcelId(null); // Reset parcel when project changes
    },
    parcels,
    parcelId,
    setParcelId,
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
