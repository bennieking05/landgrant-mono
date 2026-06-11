import * as RD from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/cn";

export const DropdownMenu = RD.Root;
export const DropdownMenuTrigger = RD.Trigger;

export function DropdownMenuContent({
  className,
  align = "end",
  sideOffset = 6,
  ...props
}: React.ComponentProps<typeof RD.Content>) {
  return (
    <RD.Portal>
      <RD.Content
        align={align}
        sideOffset={sideOffset}
        className={cn(
          "z-50 min-w-[12rem] overflow-hidden rounded-card border border-slate-200 bg-white p-1 shadow-overlay",
          className,
        )}
        {...props}
      />
    </RD.Portal>
  );
}

export function DropdownMenuItem({ className, ...props }: React.ComponentProps<typeof RD.Item>) {
  return (
    <RD.Item
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-control px-2.5 py-2 text-small text-slate-700 outline-none",
        "data-[highlighted]:bg-slate-100 data-[highlighted]:text-slate-900",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export function DropdownMenuLabel({ className, ...props }: React.ComponentProps<typeof RD.Label>) {
  return (
    <RD.Label
      className={cn("px-2.5 py-1.5 text-caption font-medium text-slate-500", className)}
      {...props}
    />
  );
}

export function DropdownMenuSeparator({
  className,
  ...props
}: React.ComponentProps<typeof RD.Separator>) {
  return <RD.Separator className={cn("my-1 h-px bg-slate-200", className)} {...props} />;
}
