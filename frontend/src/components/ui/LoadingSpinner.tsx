import { Loader2 } from "lucide-react";

type Props = {
  text?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-8 w-8",
};

export function LoadingSpinner({ text, size = "md", className = "" }: Props) {
  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <Loader2 className={`animate-spin text-brand ${sizeClasses[size]}`} />
      {text && <span className="text-sm text-slate-600">{text}</span>}
    </div>
  );
}
