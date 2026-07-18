# Real Estate Proposal Engine (v2)

A CRE brochure/PPTX/PDF generation engine, built from the ground up around the
gaps a real Cushman & Wakefield brochure ("Office Shortlist · Amsterdam 2026",
prepared for Perry Ellis, Houthavens, May 2026) exposed in a flat, one-record-
per-listing data model — including a genuine pricing inconsistency the
brokerage itself shipped. See the project spec for the full v1 → v2 rationale;
the table below is the short version.

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

## Architecture

```
backend/   FastAPI + SQLAlchemy + Pydantic — the actual engine
  app/models/       §5 data model (Building, Unit, AddOn, Neighbourhood, Client, Proposal)
  app/services/      business logic
    qa.py                §8  — single-source-of-truth, TBD gating, copy lint, price outliers
    comparison.py        §16 — all-in rate + estimated annual cost, default sort
    matching.py          §12 — Property Matching scores Units, not just Buildings
    description_generator.py  §9  — pluggable AI copy provider (deterministic fallback)
    assistant.py          §17 — pluggable NL query parser (regex fallback) + email drafting
    image_engine.py       §10 — dedupe + category ranking (real); download/upscale (documented stub)
    maps.py                §11 — static-map URL builders (need a real API key to resolve)
    scraping/              §7  — subdivision-preserving parsing (real); live fetch (documented stub)
    brochure/
      pptx_generator.py    §14 — PowerPoint as the primary render target
      pdf_export.py         §14 — PDF as a flattened export of the same slides (LibreOffice headless)
      one_pager.py           §15 — single-slide executive summary
      theme.py                §22 — white-labelable palette
    export_formats.py      §20 — CSV / Excel / Word
  app/routers/        REST API — one file per resource/concern
  app/seed/            reference-brochure demo dataset
  tests/               39 tests — pytest

frontend/  Next.js (App Router) + TypeScript + Tailwind
  src/app/             Dashboard (§18), Buildings & Units, Clients, Proposals (list/new/detail)
  src/components/       QAPanel, ComparisonTable, ExportPanel — the Proposal detail workspace
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
7-unit, 4-building Amsterdam dataset and jump straight into a populated
Proposal.

### Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest
```

39 tests, each traceable to either a spec section or a specific line in the
reference brochure's gap table (§1) — e.g. `test_flags_service_charge_mismatch_between_sources`
regression-tests the exact €55/€60 conflict shape.

## Workflows (§4)

1. **From the database** — `POST /proposals` with a `client_id` and an ordered
   `unit_ids` list, or build it interactively at `/proposals/new` in the
   frontend. Every export reads from that one Proposal record.
2. **From external URLs** — `app/services/scraping/generic_scraper.py`
   implements the subdivision-preserving parsing logic ("581 m², units from
   150 m²" → total + minimum divisible, never collapsed) as pure, tested
   functions. The live-fetch half (`fetch_rendered_html`, via the
   pre-installed Playwright Chromium) needs outbound network access to
   arbitrary third-party listing sites, which this environment doesn't have —
   it's implemented and documented but not exercised by the test suite.

## What's a real implementation vs. a documented stub

Fully implemented, tested, and exercised end-to-end (backend tests + a live
browser run against both servers):

- Data model, seed data, QA pass, Comparison Generator, PPTX/PDF/one-pager
  generation, CSV/Excel/Word/JSON export, Property Matching, Dashboard,
  the assistant's regex-based NL parser, and the full Next.js frontend.

Documented, pluggable interfaces with a working deterministic fallback,
left for a real integration once credentials/network are available:

- **§9/§17 AI copy & assistant** — `get_description_provider()` returns a
  template-based provider today; swap in an LLM-backed one behind the same
  interface.
- **§11 Maps** — URL builders are correct and provider-agnostic; resolving
  actual tiles needs `GOOGLE_MAPS_API_KEY` / `MAPBOX_ACCESS_TOKEN`.
- **§10 Image Engine** — dedupe and category-ranking logic is real; the
  download/upscale/perspective-correction pipeline needs network access to
  source images and an ML stack, and is documented as a `NotImplementedError`
  plug point.
- **§7 Scraping (live fetch)** — see Workflows above.

Every one of these is a config/credential change away from being live, not a
rewrite — that boundary was a deliberate design choice given this
environment's constraints, not an oversight.

## Design (§22)

Default theme is the reference brochure's own palette (near-black title
cards, single red accent, white detail pages) — see
`backend/app/services/brochure/theme.py`'s `Theme` dataclass. Pass a
different `Theme` into the PPTX/one-pager generators to white-label per
brokerage/tenant-rep firm.
