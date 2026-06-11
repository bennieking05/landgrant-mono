import type { Persona } from "@/context";

/** Paths each persona may open (must stay in sync with route guards). */
export const personaNavMap: Record<Persona, string[]> = {
  landowner: ["/", "/portal"],
  land_agent: ["/", "/workbench", "/ops", "/intake"],
  in_house_counsel: ["/", "/workbench", "/counsel", "/ops", "/intake"],
  outside_counsel: ["/", "/counsel"],
  firm_admin: ["/", "/firm-admin"],
  platform_admin: [
    "/",
    "/portal",
    "/intake",
    "/workbench",
    "/counsel",
    "/ops",
    "/firm-admin",
    "/admin",
  ],
};
