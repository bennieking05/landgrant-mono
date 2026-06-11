# Accessibility (WCAG 2.1 AA)

LandGrantIQ targets **WCAG 2.1 Level AA**. Public-power and large utility buyers
routinely request a VPAT during procurement; this document is the groundwork for
that artifact and the standard every new screen is held to.

## Conformance target

- **Standard:** WCAG 2.1, Level AA (also satisfies 2.0 A/AA).
- **Scope:** the React portal in `frontend/` — enterprise workbench *and* the
  landowner consumer portal.
- **Status:** automated axe checks pass with **zero serious/critical violations**
  on covered routes; manual checks tracked below.

## What is implemented

### Structure & navigation
- **Skip link** ("Skip to content") as the first focusable element in both the
  enterprise shell (`AppLayout`) and the landowner portal (`PortalLayout`),
  targeting `#main-content`.
- Single `<main id="main-content">` landmark per layout; `<header>`, `<nav>`,
  and `<footer>` landmarks with `aria-label`s where multiple exist.
- Per-route document titles via `useDocumentTitle` ("LandGrantIQ — <Page>") so
  screen-reader and 20-tab users always know where they are.

### Keyboard & focus
- Global visible focus ring via `:focus-visible` (see `src/index.css`); never
  removed without an equivalent.
- All interactive controls are real `<button>` / `<a>` / form elements (Radix
  primitives for menus, dialogs, tabs, tooltips, toasts) — full keyboard paths,
  focus trapping in dialogs, and `Esc` to dismiss come for free.
- Decision actions in the landowner portal are native buttons, fully operable by
  keyboard.

### Forms (labels & validation)
- Inputs are wrapped by the `Field` primitive, which binds `label[for]` ↔ input
  `id`, marks required fields, renders hints, and associates inline errors via
  `aria-describedby` / `aria-invalid`.
- Errors attach to the field rather than appearing as anonymous red strings;
  submit feedback is surfaced through the toast system, not silent failure.

### Status without relying on color
- Stage and risk are shown with **text + shape**, not color alone
  (`StageBadge`, `RiskBadge`).
- Health/probe dots (e.g. `OpsPage`) pair the colored dot with an `aria-label`
  and an adjacent visible text label.

### Live regions
- Toasts use Radix Toast (`aria-live="polite"` / `assertive`).
- Landowner decision flow announces submission progress (`aria-live="polite"`),
  the confirmation (`role="status"`), and errors (`role="alert"`).

### Contrast & typography
- Semantic color tokens (`success/warning/danger/info` with `bg`/`border`/`fg`
  pairs) are chosen to meet 4.5:1 for body text and 3:1 for large text/UI.
- Disciplined type scale (`display/h1…caption`) with Inter; minimum body size
  14px. The landowner portal uses larger type and plain language (6th–8th grade)
  for its non-expert, mobile audience.

### Internationalization
- UI is translatable (`react-i18next`); the landowner portal ships English and
  Spanish, with `lang` driven by the active locale.

## Automated testing

axe-core runs in Playwright and **in CI** (`.github/workflows/ci.yml`,
"Run axe accessibility checks"):

```bash
cd frontend
npm run test:a11y
```

The suite (`tests/e2e/a11y-portal-workbench.spec.ts`) fails the build on any
`serious` or `critical` violation across `wcag2a`, `wcag2aa`, `wcag21a`,
`wcag21aa` tags.

## Manual checks (per release)

Automated tools catch ~30–40% of issues. Before a release, verify:

- [ ] Tab through each primary screen — visible focus everywhere, logical order,
      no keyboard traps, skip link works.
- [ ] Operate menus, dialogs, tabs, command palette (Cmd-K) by keyboard only.
- [ ] Screen-reader smoke test (VoiceOver / NVDA) on login, dashboard, parcel
      grid, parcel detail, and the landowner portal flow.

### VoiceOver (macOS Safari) — 10-minute script

1. Enable VoiceOver (Cmd+F5). Open `/login`; confirm VO reads the page title and form labels.
2. Tab to email and password fields; verify each announces its visible label.
3. After sign-in, land on `/`; confirm the main landmark and `h1` for the dashboard.
4. Open Cmd-K; arrow through command results; Esc closes without focus loss.
5. Navigate to Workbench; verify the parcel grid table has column headers read on cell entry.
6. Open a parcel detail URL; confirm tabs are announced as tablist and panel content updates.

### NVDA (Windows Chrome) — 10-minute script

1. Start NVDA, open `/login`; single-letter navigation `f` finds edit fields with labels.
2. Tab through sign-in; activate primary button; wait for route change announcement.
3. On dashboard, `h` jumps through headings; confirm KPI region and section headings.
4. Workbench: enter table with `t`; use Ctrl+Alt+arrows to move cells; verify stage badges read text labels.
5. Landowner `/portal`: confirm step indicator and decision controls expose state (pressed/expanded as applicable).

- [ ] 200% browser zoom and 320px width: no loss of content or function.
- [ ] Confirm color is never the sole signifier of state.

## VPAT groundwork

This document plus the passing axe suite and manual checklist are the inputs for
a VPAT 2.x (WCAG edition). Track open exceptions as GitHub issues labeled
`a11y` so the "Remarks and Explanations" column stays accurate.
