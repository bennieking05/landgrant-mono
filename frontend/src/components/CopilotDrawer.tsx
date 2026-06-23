import { useEffect, useRef, useState } from "react";
import { CopilotPanel } from "@/components/CopilotPanel";

type Props = {
  open: boolean;
  onClose: () => void;
  caseId?: string;
  parcelId?: string;
  jurisdiction?: string;
};

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Accessible drawer chrome around the AI Copilot.
 *
 * Responsive by design: on desktop it's a docked, non-modal side panel (the
 * page shifts with `md:mr-96` so the workspace stays usable beside it); on
 * small screens it's a modal overlay with a click-away backdrop. The dialog
 * a11y contract is honored in both modes — labelled `role="dialog"`,
 * Esc-to-close, and focus restored to the trigger on close — and the modal
 * (mobile) mode additionally sets `aria-modal` and traps Tab focus, which would
 * be wrong on the non-modal desktop panel.
 */
export function CopilotDrawer({ open, onClose, caseId, parcelId, jurisdiction }: Props) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  // Whether this instance behaves as a modal (small screens). Captured when the
  // drawer opens so trap/aria-modal stay consistent for the session.
  const [modal, setModal] = useState(false);

  useEffect(() => {
    if (!open) return;
    // Remember what to return focus to (the toggle button), and whether we're
    // a modal right now.
    restoreFocusRef.current = (document.activeElement as HTMLElement) ?? null;
    const isModal = window.matchMedia("(max-width: 767px)").matches;
    setModal(isModal);

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && isModal && drawerRef.current) {
        const focusables = Array.from(
          drawerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
        ).filter((el) => el.offsetParent !== null);
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      // Return focus to whatever opened the drawer.
      restoreFocusRef.current?.focus?.();
    };
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
        ref={drawerRef}
        className="fixed inset-y-0 right-0 z-50 flex w-[88%] max-w-md flex-col shadow-overlay md:w-96 md:max-w-none"
        role="dialog"
        aria-label="AI Copilot"
        aria-modal={modal || undefined}
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
