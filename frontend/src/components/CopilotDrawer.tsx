import { useEffect } from "react";
import { CopilotPanel } from "@/components/CopilotPanel";

type Props = {
  open: boolean;
  onClose: () => void;
  caseId?: string;
  parcelId?: string;
  jurisdiction?: string;
};

/**
 * Drawer chrome around the AI Copilot. The panel was previously a bare
 * `fixed right-0 w-96` element with no way to dismiss it except the toggle and
 * no backdrop, and on mobile it overlapped the page. This wrapper adds:
 *  - Esc-to-close,
 *  - a click-away backdrop on small screens (where it's a modal overlay),
 *  - full-width-up-to-md layout on mobile, docked `w-96` on desktop.
 * On desktop the page shifts content with `md:mr-96` so the panel sits beside
 * the content (no backdrop there, so the workspace stays interactive).
 */
export function CopilotDrawer({ open, onClose, caseId, parcelId, jurisdiction }: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Mobile-only click-away backdrop (desktop keeps the workspace usable). */}
      <div
        className="fixed inset-0 z-40 bg-navy-950/40 md:hidden"
        aria-hidden
        onClick={onClose}
      />
      <div
        className="fixed inset-y-0 right-0 z-50 flex w-[88%] max-w-md flex-col shadow-overlay md:w-96 md:max-w-none"
        role="dialog"
        aria-label="AI Copilot"
      >
        <CopilotPanel
          caseId={caseId}
          parcelId={parcelId}
          jurisdiction={jurisdiction}
          isOpen
          onClose={onClose}
        />
      </div>
    </>
  );
}
