import * as RD from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

export const Dialog = RD.Root;
export const DialogTrigger = RD.Trigger;
export const DialogClose = RD.Close;

export function DialogContent({
  className,
  children,
  title,
  description,
  ...props
}: React.ComponentProps<typeof RD.Content> & { title: string; description?: string }) {
  return (
    <RD.Portal>
      <RD.Overlay className="fixed inset-0 z-50 bg-navy-950/40 backdrop-blur-sm" />
      <RD.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-[92vw] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-modal border border-slate-200 bg-white p-6 shadow-overlay focus:outline-none",
          className,
        )}
        {...props}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <RD.Title className="text-h2 text-slate-900">{title}</RD.Title>
            {description ? (
              <RD.Description className="mt-1 text-small text-slate-600">
                {description}
              </RD.Description>
            ) : null}
          </div>
          <RD.Close
            className="rounded-control p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </RD.Close>
        </div>
        {children}
      </RD.Content>
    </RD.Portal>
  );
}
