import { createContext, useCallback, useContext, useMemo, useState } from "react";
import * as RT from "@radix-ui/react-toast";
import { CheckCircle2, Info, AlertTriangle, XCircle, X } from "lucide-react";
import { cn } from "@/lib/cn";

type ToastVariant = "success" | "error" | "info" | "warning";

type ToastItem = {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
};

type ToastInput = {
  title: string;
  description?: string;
  variant?: ToastVariant;
};

type ToastContextValue = {
  toast: (input: ToastInput) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: "border-success-border",
  error: "border-danger-border",
  info: "border-info-border",
  warning: "border-warning-border",
};

const VARIANT_ICON = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
} as const;

const VARIANT_ICON_COLOR: Record<ToastVariant, string> = {
  success: "text-success",
  error: "text-danger",
  info: "text-info",
  warning: "text-warning",
};

let counter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const remove = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((input: ToastInput) => {
    const id = ++counter;
    setItems((prev) => [...prev, { id, variant: "info", ...input }]);
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (title, description) => toast({ title, description, variant: "success" }),
      error: (title, description) => toast({ title, description, variant: "error" }),
    }),
    [toast],
  );

  return (
    <ToastContext.Provider value={value}>
      <RT.Provider swipeDirection="right" duration={5000}>
        {children}
        {items.map((t) => {
          const Icon = VARIANT_ICON[t.variant];
          return (
            <RT.Root
              key={t.id}
              onOpenChange={(open) => !open && remove(t.id)}
              className={cn(
                "flex w-full items-start gap-3 rounded-card border bg-white p-3 shadow-overlay",
                "data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out",
                VARIANT_STYLES[t.variant],
              )}
            >
              <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", VARIANT_ICON_COLOR[t.variant])} aria-hidden />
              <div className="min-w-0 flex-1">
                <RT.Title className="text-small font-semibold text-slate-900">{t.title}</RT.Title>
                {t.description ? (
                  <RT.Description className="mt-0.5 text-caption text-slate-600">
                    {t.description}
                  </RT.Description>
                ) : null}
              </div>
              <RT.Close className="rounded p-0.5 text-slate-400 hover:text-slate-700" aria-label="Dismiss">
                <X className="h-4 w-4" />
              </RT.Close>
            </RT.Root>
          );
        })}
        <RT.Viewport className="fixed right-4 top-4 z-[100] flex w-[22rem] max-w-[calc(100vw-2rem)] flex-col gap-2 outline-none" />
      </RT.Provider>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
