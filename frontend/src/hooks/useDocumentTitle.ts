import { useEffect } from "react";

const SUFFIX = "LandGrantIQ";

/**
 * Per-route document title (UX-2): "Parcels - Highway 281 - LandGrantIQ".
 * Pass ordered segments most-specific first; the brand suffix is appended.
 */
export function useDocumentTitle(...segments: Array<string | null | undefined>) {
  const parts = segments.filter((s): s is string => Boolean(s && s.trim()));
  const title = [...parts, SUFFIX].join(" - ");
  useEffect(() => {
    const previous = document.title;
    document.title = title;
    return () => {
      // Avoid clobbering a newer route's title: if another screen already updated
      // document.title, do not restore our snapshot (fixes SPA navigation races).
      if (document.title === title) {
        document.title = previous;
      }
    };
  }, [title]);
}
