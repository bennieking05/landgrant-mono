import { AlertCircle, RefreshCw } from "lucide-react";

type Props = {
  message: string;
  onRetry?: () => void;
  className?: string;
};

export function ErrorMessage({ message, onRetry, className = "" }: Props) {
  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 ${className}`}
      role="alert"
    >
      <div className="flex items-center gap-2">
        <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-600" />
        <p className="text-sm text-rose-700">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 rounded-md bg-rose-100 px-3 py-1.5 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-200"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      )}
    </div>
  );
}
