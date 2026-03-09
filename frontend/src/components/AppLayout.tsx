"use client";

import { Link, useLocation } from "react-router-dom";
import { useAppContext } from "@/context";
import {
  Home,
  FileInput,
  Briefcase,
  Scale,
  Settings,
  ChevronDown,
  Building2,
  ShieldCheck,
} from "lucide-react";

const navItems = [
  { path: "/", label: "Home", icon: Home },
  { path: "/intake", label: "Intake", icon: FileInput },
  { path: "/workbench", label: "Workbench", icon: Briefcase },
  { path: "/counsel", label: "Counsel", icon: Scale },
  { path: "/ops", label: "Operations", icon: Settings },
  { path: "/firm-admin", label: "Firm Admin", icon: Building2 },
  { path: "/admin", label: "Admin", icon: ShieldCheck },
];

type Props = {
  children: React.ReactNode;
};

export function AppLayout({ children }: Props) {
  const location = useLocation();
  const {
    projects,
    projectId,
    setProjectId,
    parcels,
    parcelId,
    setParcelId,
    loading,
  } = useAppContext();

  const isHome = location.pathname === "/";

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navigation Bar */}
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Logo and Nav Links */}
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white font-bold text-sm">
                  LR
                </div>
                <span className="font-semibold text-slate-900">LandRight</span>
              </Link>

              <div className="hidden md:flex items-center gap-1">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-brand/10 text-brand"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Project/Parcel Selector - Hidden on Home page */}
            {!isHome && (
              <div className="flex items-center gap-3">
                {/* Project Selector */}
                <div className="relative">
                  <select
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    className="appearance-none rounded-md border border-slate-300 bg-white pl-3 pr-8 py-1.5 text-sm font-medium text-slate-700 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                </div>

                {/* Parcel Selector */}
                <div className="relative">
                  <select
                    value={parcelId ?? ""}
                    onChange={(e) => setParcelId(e.target.value || null)}
                    disabled={loading || parcels.length === 0}
                    className="appearance-none rounded-md border border-slate-300 bg-white pl-3 pr-8 py-1.5 text-sm font-medium text-slate-700 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    {parcels.length === 0 ? (
                      <option value="">
                        {loading ? "Loading..." : "No parcels"}
                      </option>
                    ) : (
                      parcels.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.id}
                        </option>
                      ))
                    )}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-slate-200 px-4 py-2">
          <div className="flex gap-1 overflow-x-auto">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors ${
                    isActive
                      ? "bg-brand/10 text-brand"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
