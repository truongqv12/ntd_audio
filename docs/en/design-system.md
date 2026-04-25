# Design system

> **For AI agents:** read this before adding UI components. Use the existing tokens from `frontend/src/styles.css`; do not introduce parallel scales.
>
> **For humans:** the visual language, layout primitives, and the small set of interaction rules every page follows.

## TL;DR

- **Operator workspace, not a marketing site.** Density and clarity over polish.
- **Project → engine → voice → config → queue → monitor → result** is the canonical user flow.
- **Bilingual EN + VI** by default; nothing renders without going through the i18n layer.
- Tokens live in `frontend/src/styles.css` at the top of the file. Components consume them via CSS variables — no duplicate hex literals.

## Design principles

1. **Voice-first.** Every screen serves the loop above.
2. **Project-first.** Voices, configs, jobs, and results never appear without their project context.
3. **Progressive disclosure.** Common actions: one click. Advanced parameters: behind an explicit toggle.
4. **Large-context picking.** With 8 engines and dozens of voices, a plain `<select>` is not enough. The voice picker shows engine, locale, capabilities, preview, and avatar.
5. **Realtime trust.** SSE drives all live state; the user never has to refresh.
6. **Bilingual.** Every label goes through `useT()` — no hardcoded strings.

## Tokens

Defined at the top of `styles.css`:

```css
:root {
  /* Color */
  --vf-color-bg-canvas: #050913;
  --vf-color-bg-panel: rgba(14, 20, 38, 0.86);
  --vf-color-text-primary: #f7f8ff;
  --vf-color-text-secondary: rgba(219, 224, 255, 0.78);
  --vf-color-accent: #6d44ff;
  --vf-color-success: #4de08d;
  --vf-color-warning: #f2c66d;
  --vf-color-error: #ff9ab0;
  --vf-color-info: #8ec0ff;

  /* Radius */
  --vf-radius-sm: 4px;
  --vf-radius-md: 8px;
  --vf-radius-lg: 16px;

  /* Spacing (4px base) */
  --vf-space-1: 4px;
  --vf-space-2: 8px;
  --vf-space-3: 12px;
  --vf-space-4: 16px;
  --vf-space-6: 24px;
  --vf-space-8: 32px;
}
```

Always reference variables. If you need a new value, add a token first, then consume it.

## Visual direction

- Dark, modern, control-plane style.
- Card / panel surfaces with subtle borders.
- Status conveyed by color **and** icon — color alone is not accessible.
- No glossy gradients on body text or backgrounds; reserve gradients for accent elements (CTA buttons, active row highlights).

## Component rules

### Buttons

- Primary: solid accent, used at most once per view.
- Secondary: outlined / subtle background.
- Destructive: red-tinted, requires explicit phrasing ("Cancel job", "Delete project") — never just an icon.

### Inputs

- Always paired with a label; placeholder is not a label substitute.
- Error state visible inline; do not rely on toast alone.
- Disabled state is visually distinct from read-only.

### Cards / panels

- Header (title + optional action) → body → footer (optional). One pattern across pages.
- Empty states are part of the component, not an afterthought. Show what action would create the first row.

### Badges and chips

- Status badges follow `JobStatus` colors (queued/running/succeeded/failed/canceled).
- Provider chips show engine + locale.

## Information architecture

Top-level navigation:

| Route | Purpose |
|---|---|
| `/` (Dashboard) | Project rollups, recent jobs, system health glance. |
| `/jobs` | Paginated job table; filter by status, provider, project, free text. |
| `/projects` | Project CRUD + script editor entry. |
| `/voices` | Voice catalog browser. |
| `/library` | Completed artifacts, paginated. |
| `/monitor` | Provider health, log tail. |
| `/settings` | Provider credentials, defaults, schemas. |

## Core flows

### A. Create a quick job

```
Dashboard → "New job" → pick project → pick engine + voice → enter text → submit
```

Three clicks, one form. No advanced params unless the user toggles them.

### B. Browse voices across engines

```
/voices → filter by language → preview → "Use this voice" → pre-fills New Job
```

The filter set is server-side (Catalog API) so it scales with engine count.

### C. Manage a script (multi-row)

```
/projects/<key>/script → import multiline → assign voice per row → enable / disable rows
  → "Queue selected" or "Queue enabled" → wait → "Merge to master"
```

Drag-and-drop rearranges rows. Per-row voice override; per-row params editor.

### D. Watch jobs run

```
Any page → SSE delivers updates → status badge / progress / done
```

If the SSE stream drops, the UI degrades to polling — but a banner makes that visible.

## i18n

- Catalogs: `frontend/src/i18n/en.json` and `frontend/src/i18n/vi.json`.
- Provider/hook surface: `frontend/src/i18n.tsx`.
- Add a key in **both** files in the same change. CI will fail if a key is missing in either.
- Do not nest more than two levels deep — keep keys flat (`jobs.create.submit`).

## What's deliberately not in this doc

- Pixel specs / mockups. Those live in design files outside the repo.
- Branding. The project is named "ntd_audio" in docs; the UI uses neutral phrasing in both languages.
- Future / aspirational components. Add them here only after they ship.
