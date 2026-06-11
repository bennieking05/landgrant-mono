# LandGrantIQ Design Tokens (UX-1)

The visual language is **institutional, precise, calm** - closer to a financial terminal than a consumer app. Tokens are the single source of truth. **Never hard-code hex, radii, or sizes in components**; consume tokens via Tailwind classes (or CSS custom properties where Tailwind cannot reach, e.g. Recharts, map layers, print).

- Tailwind theme: [`frontend/tailwind.config.ts`](../frontend/tailwind.config.ts)
- CSS custom properties: [`frontend/src/styles/tokens.css`](../frontend/src/styles/tokens.css)
- Base layer + focus ring + reduced-motion: [`frontend/src/index.css`](../frontend/src/index.css)

## Typography

- UI typeface: **Inter** (variable font, `@fontsource-variable/inter`) (`font-sans`). Identifiers (parcel/cause numbers, hashes): **IBM Plex Mono** (`font-mono` or `.font-id`).
- Scale (use the named sizes, not arbitrary values):

| Token | Size / line | Use |
|-------|-------------|-----|
| `text-display` | 30 / 36 semibold | Marketing / empty hero only |
| `text-h1` | 24 / 32 semibold | Page titles (internal pages use 24px, not 36px) |
| `text-h2` | 18 / 28 semibold | Section headers |
| `text-h3` | 16 / 24 semibold | Card / panel titles |
| `text-body` | 14 / 20 | Default body |
| `text-small` | 13 / 18 | Secondary text |
| `text-caption` | 12 / 16 tracked | Eyebrow / uppercase labels |

Numbers in tables/KPIs use `tabular-nums` (applied to `table` automatically).

## Color

Consume semantic tokens, not raw palette values.

- **Brand / navy**: `navy-50..950`, generated from `#1F4B99` (navy-600). `navy-900` (`#14294A`) is the logo navy. Back-compat alias `brand` (`bg-brand`, `text-brand`, `hover:bg-brand-dark`).
- **Accent (copper)**: `accent` (`#B26A2C`) - the "IQ" and sparing action accents.
- **Neutrals**: Tailwind `slate` for text/border/surface.
- **Semantic**: `success` / `warning` / `danger` / `info`, each with `.bg`, `.border`, `.fg`, and `DEFAULT` (e.g. `bg-success-bg text-success-fg border-success-border`). All meet >=4.5:1 fg-on-bg.
- **Stage ramp** (8 hues, deuteranopia-checked, **always paired with a text label** via `StageBadge`): `stage-intake`, `stage-appraisal`, `stage-offerPending`, `stage-offerSent`, `stage-negotiation`, `stage-closing`, `stage-litigation`, `stage-closed`, each `.bg/.fg/.border`.
- **Risk**: `risk-low/medium/high` `.bg/.fg/.border`. Always shown as `score + label`, never color alone.

AI features (Copilot, Settlement Predictor) use brand tokens + a small "AI" badge - **not** a separate purple/violet universe (removed in UX-1).

## Shape, space, elevation, motion

- Radius: `rounded-tight` (4px, tight chrome / focus), `rounded-control` (6px, buttons/inputs), `rounded-card` and `rounded-modal` (12px, cards and dialogs — one radius family for elevated surfaces).
- Control height: **36px** (`h-9`) for buttons/inputs/selects.
- Spacing: prefer the documented ramp in `tailwind.config.ts` (`spacing` extend) — multiples of **4px** (`1` = 4px, `2` = 8px, …); use named extras (`13`, `15`, …) only when the default scale is insufficient.
- Elevation: two levels only - `shadow-card`, `shadow-overlay`.
- Motion: `duration-fast` (150ms) hover/focus, `duration-base` (200ms) enter/exit, `ease-out`. Reduced-motion honored globally.

### UX-1 legacy color codemod (purple / violet purge)

These components were updated to consume semantic / stage / navy tokens instead of raw `purple-*` / `violet-*` utilities (AI and workflow UI stays in the brand system):

- `frontend/package.json` (Inter variable font package)
- `frontend/src/index.css`
- `frontend/tailwind.config.ts`
- `frontend/src/styles/tokens.css`
- `frontend/src/components/DocumentExtraction.tsx`
- `frontend/src/components/LitigationPanel.tsx`
- `frontend/src/components/AIDecisionReview.tsx`
- `frontend/src/components/NegotiationPanel.tsx`
- `frontend/src/components/TaskManager.tsx`

## Loading, timeouts & optimistic UI (UX-11)

- **Skeletons** for first loads (`Skeleton`, `SkeletonText`, `SkeletonTable`); spinners only for short in-place refreshes.
- **Timeout:** data loads via [`useAsyncResource`](../frontend/src/hooks/useAsyncResource.ts) fail after **10s** (`Promise.race`) into the error state with a retry - never an infinite spinner.
- **Safe optimistic UI:** mutations that update the UI ahead of the server use [`useOptimisticAction`](../frontend/src/hooks/useOptimisticAction.ts), which snapshots prior state and **rolls back on failure**. The UI must never lie about a failed write.
- **Performance budget:** `frontend/lighthouserc.json` enforces Lighthouse budgets in CI (`.github/workflows/lighthouse.yml`).

## Focus & accessibility

A 2px `navy-600` focus ring (`:focus-visible`) is applied globally in the base layer. Do not remove outlines without an equivalent visible focus style.
