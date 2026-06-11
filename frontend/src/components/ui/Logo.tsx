import { cn } from "@/lib/cn";

type LogoProps = {
  /** Full horizontal wordmark from official SVG; "mark" is the 3×3 grid only. */
  variant?: "full" | "mark";
  /**
   * Display height in CSS pixels. For `full`, this sets the rendered height and
   * width scales with aspect ratio (~4.55:1). For `mark`, height and width match.
   */
  size?: number;
  className?: string;
};

const FULL_SRC = "/logo-landgrantiq.svg";
const MARK_SRC = "/logo-mark.svg";

/** LandGrantIQ brand logo — official vector assets in `frontend/public/`. */
export function Logo({ variant = "full", size = 28, className = "" }: LogoProps) {
  if (variant === "mark") {
    return (
      <img
        src={MARK_SRC}
        width={size}
        height={size}
        alt="LandGrantIQ"
        className={cn("shrink-0 select-none", className)}
        draggable={false}
      />
    );
  }

  return (
    <img
      src={FULL_SRC}
      alt="LandGrantIQ"
      className={cn("h-auto w-auto max-w-[min(100%,280px)] shrink-0 select-none", className)}
      style={{ height: size, width: "auto" }}
      draggable={false}
    />
  );
}
