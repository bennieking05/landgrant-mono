import * as RT from "@radix-ui/react-tooltip";
import { cn } from "@/lib/cn";

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <RT.Provider delayDuration={300}>{children}</RT.Provider>;
}

type TooltipProps = {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "right" | "bottom" | "left";
};

export function Tooltip({ content, children, side = "top" }: TooltipProps) {
  return (
    <RT.Root>
      <RT.Trigger asChild>{children}</RT.Trigger>
      <RT.Portal>
        <RT.Content
          side={side}
          sideOffset={6}
          className={cn(
            "z-50 max-w-xs rounded-control bg-navy-900 px-2.5 py-1.5 text-caption font-medium text-white shadow-overlay",
            "data-[state=delayed-open]:animate-in data-[state=closed]:animate-out",
          )}
        >
          {content}
          <RT.Arrow className="fill-navy-900" />
        </RT.Content>
      </RT.Portal>
    </RT.Root>
  );
}
