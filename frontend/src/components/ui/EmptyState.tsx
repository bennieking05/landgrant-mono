import { type LucideIcon, Inbox } from "lucide-react";

type Props = {
  icon?: LucideIcon;
  title?: string;
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
};

export function EmptyState({
  icon: Icon = Inbox,
  title,
  message,
  action,
  className = "",
}: Props) {
  return (
    <div className={`flex flex-col items-center justify-center py-8 ${className}`}>
      <div className="rounded-full bg-slate-100 p-3">
        <Icon className="h-6 w-6 text-slate-400" />
      </div>
      {title && (
        <h4 className="mt-3 text-sm font-medium text-slate-900">{title}</h4>
      )}
      <p className="mt-1 text-sm text-slate-500">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand/90"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
