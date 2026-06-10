import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { PersonaRoute } from "@/components/PersonaRoute";
import type { Persona } from "@/context";
import { AppContext, type AppContextValue } from "@/context/AppContext";

function renderWithPersona(persona: Persona, initialPath: string) {
  const stub: AppContextValue = {
    projects: [],
    projectId: "",
    setProjectId: () => {},
    parcels: [],
    parcelId: null,
    setParcelId: () => {},
    persona,
    loading: false,
    error: null,
    refreshParcels: () => {},
  };
  return render(
    <AppContext.Provider value={stub}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/admin"
            element={
              <PersonaRoute path="/admin">
                <div data-testid="admin-content">admin</div>
              </PersonaRoute>
            }
          />
          <Route path="/" element={<div data-testid="home">home</div>} />
        </Routes>
      </MemoryRouter>
    </AppContext.Provider>,
  );
}

describe("PersonaRoute", () => {
  it("allows platform_admin to open /admin", () => {
    renderWithPersona("platform_admin", "/admin");
    expect(screen.getByTestId("admin-content")).toBeInTheDocument();
  });

  it("redirects landowner away from /admin", () => {
    renderWithPersona("landowner", "/admin");
    expect(screen.queryByTestId("admin-content")).not.toBeInTheDocument();
    expect(screen.getByTestId("home")).toBeInTheDocument();
  });
});
