# Close Acceleration Pack — Frontend

A standalone, deployable web UI for the [Close Acceleration Pack](../README.md)
project: a finance-first FP&A monthly-close workflow for the fictional
consumer-goods company Beacon Outdoor Goods. React + TypeScript + Tailwind,
built for a finance audience — the technical stack is a differentiator,
not the headline.

All data shown is **synthetic / fictional portfolio data**, clearly
disclosed in the app itself.

## What's here

Four views, routed as tabs:

- **Executive Overview** — six executive KPI cards, three trend charts, management insights.
- **Variance Analysis** — Actual vs. Budget/Forecast toggle, P&L variance table, driver lists, OI waterfall bridge.
- **Close Checklist & Controls** — Day 1–5 close calendar with dependency-cascade status, 12-control testing log.
- **Outputs** — download links for the three real Excel deliverables, plus a link to the source repo.

## Architecture

This app has **no financial logic of its own**. It reads static JSON
exported from the Python backend by
[`../scripts/export_frontend_data.py`](../scripts/export_frontend_data.py),
which calls the existing `close_pack.variance` / `close_pack.kpi` /
`close_pack.controls` modules directly — the same functions that build the
Excel workbooks — and serializes their output to `src/data/*.json`. Every
component reads that data through one adapter (`src/lib/adapter.ts`); no
component imports the JSON files directly, so swapping the data source
later (e.g. for a real API) only touches that one file.

```
src/
  lib/
    types.ts      # mirrors the JSON contract field-for-field
    adapter.ts     # the only place that imports the raw JSON
    format.ts      # finance formatters ($K, %, bps — same conventions as the backend)
    status.ts       # RAG / task-status / control-status -> color mapping
  components/       # shared UI (Card, Badge, ...) + per-tab components
  pages/            # one file per tab (Overview, Variance, Close, Outputs)
```

## Setup & run

Requires the backend data to exist first (from the repo root):

```bash
# repo root
make all            # seeds data/close_pack.db, writes output/*.xlsx
make frontend-data  # copies output/*.xlsx -> deliverables/, writes
                     # frontend/src/data/*.json + frontend/public/ assets
```

Then:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Other commands:

```bash
npm run build     # type-checks (tsc -b) and builds static frontend/dist/
npm run preview   # serves the production build locally
npm run lint       # oxlint
```

`npm run build` produces a fully static site — deployable to Vercel,
Netlify, GitHub Pages, or any static host with zero server configuration.
Routing is hash-based (`/#/variance`) so a direct link to any tab works
without a rewrite rule.

## Updating the data

The frontend has no independent data source — it can't go stale on its
own, but it also won't pick up new numbers until re-exported. After any
change to the dataset or the calculation engine, re-run `make
frontend-data` from the repo root and rebuild.

## Stack

- [Vite](https://vite.dev/) + React 19 + TypeScript
- [Tailwind CSS v4](https://tailwindcss.com/) (`@tailwindcss/vite`, no separate config file — theme tokens live in `src/index.css`)
- [Recharts](https://recharts.org/) for charts (lazy-loaded per route to keep the initial bundle small)
- [react-router-dom](https://reactrouter.com/) (`HashRouter`) for the four tabs
