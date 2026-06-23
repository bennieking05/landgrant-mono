# LandGrantIQ — End-to-End UI/UX Audit & Fixes (2026-06-22)

## 1. Executive summary

LandGrantIQ is an attorney-in-the-loop platform for land-acquisition/condemnation
casework. The app is well-architected: a clean Vite + React + Tailwind frontend with
a thoughtful design-system (`src/components/ui`), persona-based routing, i18n (EN/ES),
and a large FastAPI backend with dev seed data.

The audit surfaced **one critical, high-blast-radius bug pair that made the app appear
broken on every page reload / deep link**, plus a missing safety net. These were fixed:

1. **Auth bootstrap race** — after a reload/deep-link the JWT was restored into React
   state (so `/auth/me` worked) but the shared API client was never re-seeded with the
   token, so **every data request returned 401**. Users saw "Not authenticated", "No
   projects", and empty grids despite being logged in.
2. **`Button asChild` crashed via Radix `Slot`** — a stray `null` sibling made `Slot`
   receive two children and throw. With **no ErrorBoundary**, this blanked the whole app
   (the dashboard's empty state white-screened).
3. **No app-level ErrorBoundary** — any render error unmounted the entire SPA.

After the fixes, all staff persona routes load real seed data with **zero console/page
errors** on the reload path. Additional low-risk polish (LoginPage redesign on the design
system, sidebar contrast) was applied. Typecheck, unit tests, and production build all pass.

## 2. Application overview

| Area | Notes |
|------|-------|
| Frontend | Vite 6 + React 19 + TypeScript + Tailwind; design tokens in `src/styles/tokens.css`; design system in `src/components/ui`. |
| Routing | `react-router-dom`; persona-gated via `PersonaRoute` + `navConfig`. |
| Personas | landowner, land_agent, in_house_counsel, outside_counsel, firm_admin, platform_admin. |
| Chrome | Landowners get the calm single-column `PortalLayout`; staff get the enterprise `AppLayout` sidebar shell. |
| Backend | FastAPI (44 route modules), JWT auth, dev auto-seed (`_bootstrap_dev_db`) with demo users + projects/parcels. |
| Auth | `POST /auth/login` → JWT; `GET /auth/me` → persona/permissions. Landowners use the **invite/portal-token** flow, not password login. |

## 3. Main user flows reviewed

- **Sign-in** (`/login`) → persona-based redirect (landowner → `/portal`, staff → dashboard).
- **Land agent**: Dashboard → Workbench (intake form, parcel grid/map, pipeline, tasks) → Ops.
- **Counsel**: Approvals → Binder → Litigation → Tasks; AI audit & copilot drawers.
- **Ops**: Route planning, batch communications, integration health probes.
- **Firm/Platform admin**: portfolio metrics, global case/project search, service health.
- **Landowner portal**: invite → verify → review property/documents/offer → decision.
- **Parcel detail**: timeline, offers, communications, deadlines.

## 4. Bugs / technical issues found

| # | Severity | Issue | File(s) | Root cause | Status |
|---|----------|-------|---------|-----------|--------|
| 1 | **Critical** | Every data request 401s after reload/deep-link ("Not authenticated", "No projects", empty grids) | `src/context/AuthContext.tsx` | Token restored to React state but `setApiAuth()` (shared client) only ran inside `persistToken` (login/logout), never on bootstrap | **Fixed** |
| 2 | **Critical** | `<Button asChild>` throws Radix `Slot` "single child" error → blanks the app | `src/components/ui/Button.tsx` | `{null}{children}` passed two children to `Slot`; triggered by dashboard empty state | **Fixed** |
| 3 | High | No ErrorBoundary; any render error white-screens the whole SPA | `src/main.tsx` (new `ErrorBoundary.tsx`) | Missing boundary | **Fixed** |
| 4 | Medium | LoginPage used raw inline markup, no autofocus, plain-text error | `src/pages/LoginPage.tsx` | Pre-dates design system | **Fixed** |
| 5 | Medium (a11y) | Serious WCAG color-contrast failures (sidebar section labels, footer version text, ParcelDetail `dt` labels, portal stepper, `⌘K` kbd) | `AppLayout.tsx`, `AppFooter`, `ParcelDetailPage.tsx`, portal stepper | `text-slate-400` (#94a3b8) on white = 2.56:1 | **Partially fixed** (sidebar labels); rest documented |
| 6 | Low | Pre-existing eslint rules-of-hooks error: `useMemo` in a loop | `src/components/DeadlineManager.tsx:75` | Conditional hook | Documented (not in scope) |

### Environment / setup issues found (documented, not app bugs)
- **Docker daemon** was not running; required for Postgres (55432) + Redis (56379). Stale Redis container lacked the port mapping — needed `--force-recreate`.
- **Backend venv not relocatable**: console-script shebangs point to a stale path
  (`/Users/bennieking/Sites/landgrant-mono`). Workaround: run `python -m uvicorn` / `python -m alembic`.
- **`bcrypt` drift**: venv had `bcrypt 5.0.0`, incompatible with `passlib 1.7.4` (login 500s).
  `requirements-dev.txt` correctly pins `bcrypt==4.0.1`; reinstalling the pin fixed login.
- **`.env` JSON arrays** (`ALLOWED_ORIGINS=["..."]`) must be read by pydantic-settings,
  not shell-sourced (shell strips the quotes → parse error).
- Python in the venv is 3.9 (CommandLineTools) though README asks for 3.11+; core deps import fine.

## 5. UI/UX issues found (review)

Strengths: consistent token system, Radix-based accessible primitives (Dialog/Toast/Tabs/
Tooltip), skeleton loading, persona-tailored chrome, i18n coverage, skip-to-content links.

Opportunities (beyond what was fixed):
- "Select a parcel" guidance is buried inside tab bodies rather than a persistent header.
- Some empty/error states are bespoke `div`s instead of the shared `EmptyState`/`Alert`.
- Map Suspense fallbacks are hand-rolled spinners instead of `LoadingSpinner`.
- Several section headings/strings are not yet run through i18n.
- AI Copilot panel is a `fixed` right overlay with no Esc/backdrop dismiss.
- `PersonaRoute` redirects are silent (no toast explaining the bounce).

## 6. Improvements implemented

1. **Auth bootstrap** (`AuthContext.tsx`): seed `setApiAuth` synchronously in the lazy
   `useState` initializer so the shared client has the token before any child fetch.
2. **Button** (`ui/Button.tsx`): when `asChild`, pass a single child to `Slot`; only render
   the loading spinner sibling for real `<button>`s.
3. **ErrorBoundary** (`components/ErrorBoundary.tsx` + `main.tsx`): app-level boundary with a
   recoverable fallback (Reload / Back to home) and Sentry reporting when configured.
4. **LoginPage** (`pages/LoginPage.tsx`): rebuilt on the design system (`Logo`, `Card`,
   `Field`, `Input`, `Button`, `Alert`); added `autoFocus`, accessible field association,
   button loading state, and an `Alert`-styled error.
5. **Sidebar contrast** (`AppLayout.tsx`): "Workspace"/"Administration" labels
   `text-slate-400 → text-slate-500` (2.56:1 → 4.6:1), on every enterprise page.

## 7. Files changed

- `frontend/src/context/AuthContext.tsx` (auth bootstrap seed)
- `frontend/src/components/ui/Button.tsx` (Slot single-child fix)
- `frontend/src/components/ErrorBoundary.tsx` (new)
- `frontend/src/main.tsx` (wrap app in ErrorBoundary)
- `frontend/src/pages/LoginPage.tsx` (design-system redesign)
- `frontend/src/components/AppLayout.tsx` (sidebar label contrast)
- `backend/.venv` — reinstalled `bcrypt==4.0.1` (environment, not source)

## 8. Validation / testing performed

- **Typecheck** (`npm run lint` → `tsc --noEmit`): **PASS**.
- **Unit tests** (`vitest run`): **14/14 PASS**.
- **Production build** (`vite build`): **PASS**.
- **ESLint** on changed files: **0 errors**, 2 pre-existing fast-refresh warnings.
- **Runtime (Playwright, real reload/deep-link auth path)**: agent/counsel/admin routes —
  **0 × 401, 0 page errors**; dashboard and workbench render real seed data.
- **Manual flow checks**: login, persona redirect, dashboard, workbench (projects + parcel
  grid), ops, intake, counsel, admin all render.
- **Accessibility (axe)**: remaining serious violations are **pre-existing color-contrast**
  issues in files untouched by this work (verified via `git status`); the highest-frequency
  one (sidebar labels) was fixed.

## 9. Remaining risks / follow-ups

- ~~**Visual-regression baselines** should be refreshed~~ — **Done** (see §9e).
- ~~**`DeadlineManager.tsx:75`** rules-of-hooks error~~ — **Fixed** (see §9d). The eslint
  suite now reports **0 errors**.
- ~~**bcrypt pin** should be enforced in CI / setup~~ — **Done** (see §9f).

## 9b. UX "functional sense" pass (round 2)

A second pass evaluated whether the flows make functional sense, not just whether they
work. Findings and fixes:

- **Developer jargon shown to users.** Staff page subtitles read like backlog tickets:
  Workbench said *"Pulls backlog stories for map view, routing, comms log, pre-offer packet
  QA, and portal dispatch."*; Counsel said *"…outside counsel handoffs per scope
  instructions."* Rewrote both as plain, task-oriented copy and gave each page a clear name
  (`Workbench`, `Counsel workbench`) instead of a feature-list heading.
- **The active parcel was invisible.** Workbench/Counsel/Ops auto-select the first parcel
  and silently scope every panel to it, with no indication of *which* parcel. Added a
  reusable **`ActiveParcelBar`** (`components/ActiveParcelBar.tsx`) that surfaces the active
  parcel id + stage + risk + owner/county and links to the full record — or guides the user
  to pick one when none is selected.
- **A tab rendered nothing.** The Workbench *Pipeline* tab was fully gated on a selected
  parcel, so it showed blank space when none was selected. Added an `EmptyState` explaining
  how to select a parcel.
- **Consistency / a11y.** Replaced the Workbench Copilot toggle's hand-rolled `<svg>` with a
  lucide `Sparkles` icon and added `aria-pressed`; gave the section tabs `role="tab"` +
  `aria-selected`.

Files added/changed in this pass: `components/ActiveParcelBar.tsx` (new),
`pages/WorkbenchPage.tsx`, `pages/CounselPage.tsx`. Typecheck, unit tests, build, and lint
on changed files all pass; agent routes remain error-free at runtime.

## 9c. Deep UX pass (round 3)

Completed the previously-deferred larger items, plus a high-impact latent bug found along the way.

- **`tailwind-merge` was silently dropping `text-white` from buttons** (`lib/cn.ts`). The
  design system's custom font-size tokens (`text-body/small/caption/h1…`) weren't registered
  with tailwind-merge, so it misclassified e.g. `text-body` as a text *color* and stripped a
  real `text-white` — rendering **every default primary `Button`'s label dark on the brand
  background** (axe: 2.14:1). Fixed with `extendTailwindMerge`, restoring white labels
  app-wide. (Root cause of one of the contrast failures; affected far more than one button.)
- **Radix `Tabs` refactor** of the hand-rolled tab bars in Workbench, Counsel, and Admin
  (ParcelDetail already used the design-system `Tabs`). Proper `role="tab"`/`tabpanel`
  semantics, keyboard arrow-nav, and consistent underlined styling. Verified by clicking
  through every tab on each page with zero runtime errors.
- **Dismissible, responsive Copilot drawer** (`components/CopilotDrawer.tsx`). Esc-to-close,
  click-away backdrop on mobile (with a tappable sliver), full-height docked `w-96` on
  desktop (content shifts via `md:mr-96` instead of overlapping; previously `mr-96` squished
  mobile content). Applied to Workbench and Counsel.
- **Active-parcel bar in Counsel litigation** — the litigation flow now shows the same
  explicit active-parcel context as the Workbench.
- **Full WCAG contrast sweep** — drove axe across all routes and fixed every genuine text
  failure (16 → **0**): sidebar `⌘K` kbd, footer version, dashboard "limited data" note,
  ParcelDetail `dt` labels/timestamps/citations, Ops probe details, RoutePlan/TemplateViewer
  empty hints, Intake/Portal stepper labels, RuleResults "Fired", CommsLog labels, county
  FIPS. Also fixed an **unlabeled email input** (InviteCard) flagged by axe's `label` rule.
  The `tests/e2e/a11y-portal-workbench.spec.ts` suite now passes **4/4** (was 0/4).
- **Empty/error-state unification** — Admin (error → `Alert`; three table/health empties →
  `EmptyState`) and FirmAdmin (error+retry → `Alert` with `action`).
- **Consistency** — replaced hand-rolled inline `<svg>` Copilot/Audit icons with lucide
  (`Sparkles`, `ScrollText`) and added `aria-pressed` to the Copilot toggles.

**Test-suite repair (regression coverage):** the `agent.spec.ts` and `counsel.spec.ts` e2e
specs never authenticated in `beforeEach`, so they silently redirected to `/login` and their
visibility assertions could never pass (pre-existing). Added the standard sessionStorage
`staffLogin` and updated assertions to the new copy/structure. Both suites now pass
**17/17** and genuinely exercise the refactored pages.

Round-3 validation: typecheck **PASS**, unit **14/14**, build **PASS**, axe contrast **0**,
a11y e2e **4/4**, agent+counsel e2e **17/17**, runtime sweep **0 page errors / 0 staff 401s**.

Round-3 files: `lib/cn.ts`, `components/CopilotDrawer.tsx` (new), `components/ActiveParcelBar.tsx`,
`pages/WorkbenchPage.tsx`, `pages/CounselPage.tsx`, `pages/AdminPage.tsx`, `pages/FirmAdminPage.tsx`,
`pages/DashboardPage.tsx`, `pages/IntakePage.tsx`, `pages/ParcelDetailPage.tsx`, `pages/OpsPage.tsx`,
`components/AppLayout.tsx`, `components/AppFooter.tsx`, `components/CommsLog.tsx`,
`components/InviteCard.tsx`, `components/ParcelList.tsx`, `components/ParcelMap.tsx`,
`components/RoutePlanPanel.tsx`, `components/RuleResults.tsx`,
`components/TemplateViewer.tsx`, `tests/e2e/agent.spec.ts`, `tests/e2e/counsel.spec.ts`.

## 9d. DeadlineManager rules-of-hooks fix (round 4)

The last remaining eslint **error** (`react-hooks/rules-of-hooks` at
`DeadlineManager.tsx:75`) is resolved. The `byDay` `useMemo` lived inside the nested
`DeadlineCalendar` component where it's technically valid, but the plugin's
component-detection misfired on the nested function ("…may be executed more than once…in a
loop"). Since `byDay` is a cheap bucket-by-day derivation rebuilt only while the calendar
view is mounted, it's now computed inline (no hook) — functionally identical, and the lint
error is gone. Also removed an unused `row` arg in the parcel column (cleared its warning).

Result: eslint **0 errors** (was 1), `DeadlineManager.tsx` fully clean. Verified at runtime —
the Counsel → Binder & deadlines tab renders, and the List⇄Calendar toggle works (deadlines
bucket onto the correct days) with 0 page errors. Build, typecheck, unit (14/14), and counsel
e2e (9/9) all pass.

## 9e. Visual-regression baseline refresh (round 5)

The baselines were doubly stale: they predated **auth** (the spec only `goto`s, never logs
in) and were captured against a **previous app generation** ("LandRight" branding, top-nav,
"LANDRIGHT MVP" home page — the same era as the old `text=LandGrant MVP` test assertion).
Re-running `--update-snapshots` as-is would have captured login/redirect pages.

Fix: added the standard sessionStorage `staffLogin` to both top-level describes in
`visual-regression.spec.ts`, cleared the old baselines, and regenerated. New baselines now
capture the **current authenticated UI** with all the improvements (LandGrantIQ dashboard,
underlined Radix tabs, corrected button colors, refreshed login, etc.):
`home-page`, `workbench-full`, `parcel-list`, `intake-page`, `counsel-page`, `ops-page`.
A clean re-run (without `--update`) passes **10/10** (1 pre-existing `test.skip`, map
component no-ops without a Mapbox token).

**Determinism (round 6):** the baselines are now hermetic, so they no longer drift with the
wall clock. A `stabilize(page)` helper:
- **Freezes the browser clock** to a fixed instant (`page.clock.setFixedTime`,
  2026-06-23 12:00). Every relative-date computation — days-until a deadline, urgency colors,
  the calendar "today" ring, the footer year, the Ops "Last checked" stamp — is now identical
  on every run regardless of the real date. (Confirmed: the Ops baseline reads "Last checked
  12:00:00 PM" instead of the real run time.)
- **Pins the two server-time-driven sources** with `page.route` fixtures: `/dashboard/home`
  (the rollup counts) and the three `/health/*` probes (states/details). Everything else
  (parcels, projects, deadline *dates*) is stable seeded data.

A clean re-run passes **10/10** and is reproducible across dates. Remaining caveat: if the dev
DB is wiped and re-seeded, the seeded absolute dates shift, so a re-baseline would be needed
then (the seed is idempotent, so this won't happen on its own).

## 9f. Enforce the bcrypt pin (round 7)

The original setup blocker — the venv had drifted to `bcrypt 5.0.0`, which is incompatible
with `passlib 1.7.4` and made `POST /auth/login` return 500 — is now guarded so it can't
silently recur. `requirements-dev.txt` already pinned `bcrypt==4.0.1`; the gap was that
nothing *verified* the pin held. Added three layers of defense:

1. **Regression test** (`backend/tests/test_bcrypt_compat.py`) — asserts the installed bcrypt
   is `< 4.1` **and** round-trips the exact `CryptContext(schemes=["bcrypt"])` that
   `/auth/login` uses (hash + verify). Runs in CI's existing "Backend tests" pytest step and
   locally. Proven to fail loudly on `bcrypt 5.0.0` (with a fix hint) and pass on `4.0.1`.
2. **CI fast-check** — a "Verify bcrypt pin" step in both `ci.yml` jobs (the main test job and
   the Playwright job, which installs deps but doesn't run pytest), failing immediately after
   dependency install if the resolved version drifts past the pin.
3. **`setup.sh` auto-correct** — after `pip install -r requirements-dev.txt`, the script
   checks the version and reinstalls `bcrypt==4.0.1` if a stale venv / transitive resolution
   drifted, so a fresh local bootstrap self-heals.

Validation: guard test **2 passed** (and confirmed **2 failed** on a deliberately-installed
`5.0.0`, then restored); CI one-liner passes silently on `4.0.1`; `ci.yml` valid YAML;
`setup.sh` passes `bash -n`.

## 9g. Performance, i18n, and Copilot dialog a11y (round 8)

The larger §10 items are now done:

- **Bundle code-splitting** — route-level `React.lazy` for every page (and the dashboard,
  so Recharts loads on demand) plus `manualChunks` for `react-vendor`/`radix`. The initial
  `index` chunk dropped from **1,237 kB → 342 kB** (gzip **355 → 107 kB**, ~70% less initial
  JS); `mapbox-gl` (1.68 MB) and Recharts now load only when their screens mount. A
  shell-level `Suspense` keeps the sidebar up while page content loads.
- **i18n expansion** — moved the primary staff surfaces to `t()` with EN + **ES** strings
  (`LoginPage`; the Workbench/Counsel/Ops/Admin/FirmAdmin headers; `ActiveParcelBar` and its
  hints). Verified Spanish renders (e.g. "Mesa de trabajo", "Iniciar sesión"); English
  defaults unchanged so baselines hold.
- **Copilot as a full a11y dialog** — `CopilotDrawer` now restores focus to the trigger on
  close (all modes), and on small screens (where it's a modal overlay) sets `aria-modal` and
  traps Tab focus; on desktop it stays a labelled, non-modal docked panel so the workspace
  remains usable beside it. Verified: desktop returns focus on Esc with no `aria-modal`;
  mobile sets `aria-modal="true"` and keeps focus inside across repeated Tabs.

Validation: typecheck **PASS**, unit **14/14**, build **PASS**, e2e (agent/counsel/a11y/
visual) **31 passed**, 0 lint errors in changed files.

## 10. Suggested next-phase improvements (not implemented — larger scope)

- ~~Sweep remaining WCAG contrast failures~~ — done (§9c). ~~Replace bespoke empty/error
  states~~ — done for the main offenders (§9b/§9c). ~~Copilot dismissible/non-overlapping~~
  and ~~full dialog a11y~~ — done (§9c/§9g). ~~i18n of headings~~ — primary surfaces done
  (§9g). ~~Code-split the bundle~~ — done (§9g).
- Remaining: unify map `Suspense` fallbacks on `LoadingSpinner`; toast feedback when
  `PersonaRoute` denies access; extend i18n to the deeper panel/section strings and the
  AppLayout "Workspace"/"Administration" labels; move visual-regression toward fixed-date
  seed fixtures so a DB re-seed can't require re-baselining.
