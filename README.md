# Real Estate Proposal Engine (v2)

A CRE brochure/PPTX/PDF generation engine, built from the ground up around
gaps found in two real reference documents:

1. A 7-listing direct-lease brochure ("Office Shortlist · Amsterdam 2026")
   whose flat, one-record-per-listing data model couldn't represent
   multi-unit buildings, TBD pricing, or a computed all-in rate — and which
   shipped a genuine cross-page pricing inconsistency.
2. A real "Market Inventory" flex-office template — diagonal red/white brand
   motif, per-desk/month pricing, region-grouped map pages, a closing
   Project Team page — which this generator's PPTX/PDF layout now matches
   directly (see [Template match](#template-match-market-inventory) below).

The table below is the short version of the first document's gap-to-fix
mapping; see the project spec for the full rationale.

| # | Gap in a flat model | Fix, and where it lives |
|---|---|---|
| 1 | One building, one price/size record | `Building` + `Unit` split — [`backend/app/models/building.py`](backend/app/models/building.py), [`unit.py`](backend/app/models/unit.py) |
| 2 | Rent as a bare number can't represent "TBD" | `rent_price_type` / `service_charge_price_type` enums — [`backend/app/models/enums.py`](backend/app/models/enums.py) |
| 3 | Same transit fact repeated on every listing | `Neighbourhood` entity, inherited by Buildings — [`neighbourhood.py`](backend/app/models/neighbourhood.py) |
| 4 | Parking costs buried in free text | `AddOn` entity — [`addon.py`](backend/app/models/addon.py) |
| 5 | Overview table and detail page can silently disagree | Single-source-of-truth rule + `check_source_conflicts` — [`services/qa.py`](backend/app/services/qa.py) |
| 6 | Contract term not modeled at all | First-class `contract_term` field on `Unit` |
| 7 | No combined €/m²/yr or annual cost | Comparison Generator computes both — [`services/comparison.py`](backend/app/services/comparison.py) |
| 8 | No concept of "a dated selection sent to one client" | `Client` + `Proposal` entities — [`client.py`](backend/app/models/client.py), [`proposal.py`](backend/app/models/proposal.py) |

## Template match ("Market Inventory")

The PPTX/PDF layout mirrors the real flex-office template page-for-page:

- **Cover** — diagonal red panel (freeform polygon, not a rotated rectangle),
  white logo bar, document type / client name / search area / date.
- **Search Profile** — corner diagonal accent, field rows from the client's
  search brief.
- **Per Region divider + region map pages** — Units are grouped by
  `Building.submarket` in first-seen order; each region gets a real
  (or gracefully-placeholdered) Google Static Maps image with one numbered
  pin per **unit** — not per building, since two units sharing a building
  (gap #1) still need two distinct, separately-numbered listings.
- **Unit fact sheets** — one page per unit: photo + numbered badge,
  CHARACTERISTICS / REMARKS columns, and an Accessibility / Transport /
  Airport stat row — replacing this generator's original 3-slide
  title-card/detail/gallery block.
- **All Properties Overview** — full map + two-column numbered address list.
- **Comparison + Recommendation** — this engine's own value-add the source
  template doesn't have (§16): a computed all-in rate / monthly cost the
  source template's author would otherwise have to work out by hand.
- **Project Team** — closing page with diagonal design and contact cards.

Two pricing models coexist because the two source documents use different
ones — see `Unit.pricing_model` (`PricingModel` enum,
[`enums.py`](backend/app/models/enums.py)):

- `per_sqm_annual` — direct lease, €/m²/year (the original 7-listing gap
  table).
- `per_desk_monthly` — flex/serviced office, €/desk/month (the Market
  Inventory template). QA (`check_tbd_headline_fields`) and the Comparison
  Generator (`build_comparison_row`/`_sort_key`) both branch on this field
  so the two are never conflated — a flex unit's price lives in
  `price_per_desk_month_eur`, not `rent_eur_per_m2_year`, and ranks
  separately in the comparison table rather than being forced onto the same
  €/m²/yr scale.

The demo seed data reflects both: 7 direct-lease units (the original gap
dataset, unchanged) plus one `per_desk_monthly` unit ("Prinseneiland 12"),
split across 2 regions ("Houthavens Waterfront" / "Houthavens Central") to
exercise the Per Region grouping.

## Architecture

```
backend/   FastAPI + SQLAlchemy + Pydantic — the actual engine
  app/models/       §5 data model (Building, Unit, AddOn, Neighbourhood, Client, Proposal)
  app/services/      business logic
    qa.py                §8  — single-source-of-truth, TBD gating (both pricing models), copy lint, price outliers
    comparison.py        §16 — all-in rate / monthly cost, pricing-model-aware sort
    matching.py          §12 — Property Matching scores Units, not just Buildings
    description_generator.py  §9  — pluggable AI copy provider (deterministic fallback)
    assistant.py          §17 — pluggable NL query parser (regex fallback) + email drafting
    image_engine.py       §10 — dedupe + category ranking (real); download/upscale (documented stub)
    maps.py                §11 — real Google Static Maps URL builder + image fetch (needs GOOGLE_MAPS_API_KEY); graceful placeholder fallback
    scraping/              §7  — subdivision-preserving parsing (real); live fetch (documented stub)
    brochure/
      pptx_generator.py    §14 — PowerPoint as the primary render target, matching the Market Inventory template
      slide_kit.py           — diagonal freeform panels, numbered badges, stat-icon rows
      pdf_export.py         §14 — PDF as a flattened export of the same slides (LibreOffice headless)
      one_pager.py           §15 — single-slide executive summary
      theme.py                §22 — white-labelable palette
    export_formats.py      §20 — CSV / Excel / Word
  app/routers/        REST API — one file per resource/concern (incl. imports.py, §7/Workflow 2)
  app/seed/            reference-brochure demo dataset (8 units / 5 buildings / 2 regions)
  tests/               47 tests — pytest

frontend/  Next.js (App Router) + TypeScript + Tailwind
  src/app/             Dashboard (§18), Buildings & Units, Import from URLs, Clients, Proposals (list/new/detail)
  src/components/       QAPanel, ComparisonTable, ExportPanel, ImportForm — the Proposal detail workspace + Workflow 2
```

## Running it

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000, tables auto-created (SQLite by default)
```

PDF export (`/proposals/{id}/export/pdf` and `/export/one-pager`) shells out to
LibreOffice headless. Only `libreoffice-core` ships filters for nothing at
all — you need the Impress component too:

```bash
sudo apt-get install -y libreoffice-impress
```

Region map pages render a real Google Static Maps image when
`GOOGLE_MAPS_API_KEY` is set; without it, `fetch_static_map_image` returns
`None` and the generator falls back to a clearly-labeled placeholder — it
never fails the export.

Point `DATABASE_URL` at Postgres (Supabase, per the spec's intended stack) in
production; SQLite is the zero-config default for local dev.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL, defaults to http://localhost:8000
npm run dev                  # http://localhost:3000
```

Click **"Load reference brochure demo data"** on the dashboard to seed the
8-unit, 5-building, 2-region Amsterdam dataset and jump straight into a
populated Proposal.

### Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest
```

47 tests, each traceable to either a spec section or a specific line in the
reference brochure's gap table (§1) — e.g. `test_flags_service_charge_mismatch_between_sources`
regression-tests the exact €55/€60 conflict shape.

## Workflows (§4)

1. **From the database** — `POST /proposals` with a `client_id` and an ordered
   `unit_ids` list, or build it interactively at `/proposals/new` in the
   frontend. Every export reads from that one Proposal record.
2. **From external URLs** — paste one or more listing URLs at `/import` in the
   frontend, or `POST /imports/urls` directly. Each URL is rendered with the
   pre-installed Playwright Chromium (`fetch_rendered_html`) and parsed with
   BeautifulSoup (`parse_html`): title, meta description, photos (logo/icon
   images filtered out), and a best-effort area/price/energy-label reading of
   the page text — preserving unit-level subdivision ("320 m², units from
   120 m²" → total + minimum divisible, never collapsed) rather than a single
   site-specific selector set per source. Every field it can't resolve is
   stored as `tbd`/omitted rather than blank or guessed (§24) — e.g. address
   extraction needs per-source selectors this generic parser doesn't have, so
   it's left `"TBD"` for a human to fill in, not invented. Each URL in a batch
   succeeds or fails independently, so one bad link doesn't block the rest.
   Verified end-to-end (real Chromium render → parse → stored Building/Unit,
   through the actual `/import` page) against a local fixture page; live
   third-party sites need outbound network access this environment doesn't
   have, so `fetch_rendered_html` itself isn't exercised by the automated
   test suite (`parse_html` and the router's create/error-handling logic are —
   see `tests/test_scraping.py` and `tests/test_imports.py`).

## What's a real implementation vs. a documented stub

Fully implemented, tested, and exercised end-to-end (backend tests + a live
browser run against both servers, including a downloaded PPTX opened and
verified, and a real Chromium-rendered import against a local fixture page):

- Data model (incl. dual pricing models), seed data, QA pass, Comparison
  Generator, PPTX/PDF/one-pager generation matching the Market Inventory
  template, CSV/Excel/Word/JSON export, Property Matching, Dashboard, the
  assistant's regex-based NL parser, URL import (Workflow 2, §7) end-to-end
  including its frontend page, and the rest of the Next.js frontend.

Documented, pluggable interfaces with a working deterministic fallback,
left for a real integration once credentials/network are available:

- **§9/§17 AI copy & assistant** — `get_description_provider()` returns a
  template-based provider today; swap in an LLM-backed one behind the same
  interface.
- **§11 Maps** — `build_region_map_url` builds a correct, provider-agnostic
  Google Static Maps request (numbered markers, grayscale style) and
  `fetch_static_map_image` will download the real tile the moment
  `GOOGLE_MAPS_API_KEY` is set; until then it returns `None` and the caller
  falls back to a placeholder rather than failing.
- **§10 Image Engine** — dedupe and category-ranking logic is real; the
  download/upscale/perspective-correction pipeline needs network access to
  source images and an ML stack, and is documented as a `NotImplementedError`
  plug point.
- **§7 Scraping (live fetch)** — see Workflows above.

Every one of these is a config/credential change away from being live, not a
rewrite — that boundary was a deliberate design choice given this
environment's constraints, not an oversight.

## Design (§22)

Default theme is the reference documents' own palette (near-black title
cards / diagonal red panels, single red accent, white detail pages) — see
`backend/app/services/brochure/theme.py`'s `Theme` dataclass. Pass a
different `Theme` into the PPTX/one-pager generators to white-label per
brokerage/tenant-rep firm.

All names in the seed data — client, brokers, buildings, the flex-office
brand "Flexspace Central" — are fictional; no real company's brochure,
staff, or contact details are reproduced anywhere, including the closing
Project Team page.
