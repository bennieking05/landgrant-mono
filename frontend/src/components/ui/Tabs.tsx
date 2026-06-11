import * as RT from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

export const Tabs = RT.Root;

export function TabsList({ className, ...props }: React.ComponentProps<typeof RT.List>) {
  return (
    <RT.List
      className={cn(
        "flex flex-wrap items-center gap-1 border-b border-slate-200",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof RT.Trigger>) {
  return (
    <RT.Trigger
      className={cn(
        "-mb-px border-b-2 border-transparent px-3 py-2 text-small font-medium text-slate-600 transition-colors duration-fast hover:text-slate-900",
        "data-[state=active]:border-brand data-[state=active]:text-brand",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({ className, ...props }: React.ComponentProps<typeof RT.Content>) {
  return <RT.Content className={cn("focus-visible:outline-none", className)} {...props} />;
}
