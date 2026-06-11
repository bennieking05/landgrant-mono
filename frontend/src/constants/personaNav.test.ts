import { describe, it, expect } from "vitest";
import { personaNavMap } from "./personaNav";

// These are regression guards for the persona gating map used by
// ``PersonaRoute``. They don't try to cover every combination — just the
// high-impact invariants that, if broken, immediately produce a routing
// defect (persona loses access to a page they should have, or gains one
// they shouldn't).

describe("personaNavMap", () => {
  it("grants platform_admin access to every gated page", () => {
    const allOther = new Set<string>();
    for (const [persona, paths] of Object.entries(personaNavMap)) {
      if (persona === "platform_admin") continue;
      for (const p of paths) allOther.add(p);
    }
    for (const p of allOther) {
      expect(personaNavMap.platform_admin).toContain(p);
    }
  });

  it("always includes the dashboard for every persona", () => {
    for (const paths of Object.values(personaNavMap)) {
      expect(paths).toContain("/");
    }
  });

  it("keeps landowners off counsel/admin surfaces", () => {
    const blocked = ["/counsel", "/admin", "/firm-admin", "/workbench", "/ops", "/intake"];
    for (const p of blocked) {
      expect(personaNavMap.landowner).not.toContain(p);
    }
    expect(personaNavMap.landowner).toContain("/portal");
  });

  it("keeps outside counsel off in-house surfaces", () => {
    const blocked = ["/workbench", "/ops", "/admin", "/firm-admin"];
    for (const p of blocked) {
      expect(personaNavMap.outside_counsel).not.toContain(p);
    }
  });

  it("firm_admin sees firm-admin but not platform admin", () => {
    expect(personaNavMap.firm_admin).toContain("/firm-admin");
    expect(personaNavMap.firm_admin).not.toContain("/admin");
  });
});
