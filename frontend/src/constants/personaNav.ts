import type { Persona } from "@/context";

/** Paths each persona may open (must stay in sync with route guards). */
export const personaNavMap: Record<Persona, string[]> = {
  landowner: ["/", "/intake"],
  land_agent: ["/", "/workbench", "/ops"],
  in_house_counsel: ["/", "/workbench", "/counsel", "/ops"],
  outside_counsel: ["/", "/counsel"],
  firm_admin: ["/", "/firm-admin"],
  admin: ["/", "/intake", "/workbench", "/counsel", "/ops", "/firm-admin", "/admin"],
};
