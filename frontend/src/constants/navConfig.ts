import {
  LayoutDashboard,
  FileInput,
  Briefcase,
  Scale,
  Settings,
  Building2,
  ShieldCheck,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import type { Persona } from "@/context";
import { personaNavMap } from "@/constants/personaNav";

export type NavItem = {
  path: string;
  labelKey: string;
  fallbackLabel: string;
  icon: LucideIcon;
  section: "workspace" | "administration";
};

/** Single source of truth for the sidebar. Filtered per persona via personaNavMap. */
export const NAV_ITEMS: NavItem[] = [
  { path: "/", labelKey: "nav.dashboard", fallbackLabel: "Dashboard", icon: LayoutDashboard, section: "workspace" },
  { path: "/portal", labelKey: "nav.portal", fallbackLabel: "My parcel", icon: UserRound, section: "workspace" },
  { path: "/intake", labelKey: "nav.intake", fallbackLabel: "Intake", icon: FileInput, section: "workspace" },
  { path: "/workbench", labelKey: "nav.workbench", fallbackLabel: "Workbench", icon: Briefcase, section: "workspace" },
  { path: "/counsel", labelKey: "nav.counsel", fallbackLabel: "Counsel", icon: Scale, section: "workspace" },
  { path: "/ops", labelKey: "nav.ops", fallbackLabel: "Operations", icon: Settings, section: "workspace" },
  { path: "/firm-admin", labelKey: "nav.firmAdmin", fallbackLabel: "Firm admin", icon: Building2, section: "administration" },
  { path: "/admin", labelKey: "nav.admin", fallbackLabel: "Platform admin", icon: ShieldCheck, section: "administration" },
];

export function navForPersona(persona: Persona): NavItem[] {
  const allowed = personaNavMap[persona] ?? [];
  return NAV_ITEMS.filter((item) => allowed.includes(item.path));
}
