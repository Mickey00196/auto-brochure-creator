"""§7 Scraping Engine — generic implementation.

`fetch_rendered_html` drives the pre-installed Playwright Chromium to render
a listing page (handles JS-heavy brokerage sites); it requires outbound
network access to the target site, which this sandbox does not have for
arbitrary third-party domains, so it's provided but not exercised by tests.

`parse_area_subdivision` and `extract_units_from_text` are pure functions
with no network dependency — they're the actual fix for §7's core
requirement (preserve subdivision instead of collapsing to one figure) and
are covered by tests/test_scraping.py against text patterns modeled on the
reference brochure.
"""
from __future__ import annotations

import re

from app.services.scraping.base import ScrapedListing, ScrapedUnit

# Matches patterns like "581 m², units from 150 m²" or "307 m² (from 75 m²)"
_SUBDIVISION_RE = re.compile(
    r"(?P<total>[\d.,]+)\s*m²[,\s(]*"
    r"(?:units?\s+)?from\s*(?P<min>[\d.,]+)\s*m²",
    re.IGNORECASE,
)

_SIMPLE_AREA_RE = re.compile(r"(?P<total>[\d.,]+)\s*m²")


def _to_float(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", ".")) if "," in raw else float(raw.replace(",", ""))


def parse_area_subdivision(text: str) -> tuple[float | None, float | None]:
    """Returns (total_area_m2, min_divisible_area_m2). Preserves subdivision
    instead of collapsing a building to a single area figure (§7)."""
    match = _SUBDIVISION_RE.search(text)
    if match:
        return _to_float(match.group("total")), _to_float(match.group("min"))

    simple = _SIMPLE_AREA_RE.search(text)
    if simple:
        return _to_float(simple.group("total")), None

    return None, None


_PRICE_RE = re.compile(r"€\s*(?P<value>[\d.,]+)")
_FROM_RE = re.compile(r"\bfrom\b", re.IGNORECASE)
_TBD_RE = re.compile(r"\b(tbd|on request|price on application|in overleg)\b", re.IGNORECASE)


def extract_price_raw(text: str) -> str:
    """Returns a raw price token: a euro amount, 'from €X', or 'tbd' — never
    blank, never a guess (§7, §24)."""
    if _TBD_RE.search(text):
        return "tbd"
    match = _PRICE_RE.search(text)
    if not match:
        return "tbd"
    prefix = "from " if _FROM_RE.search(text) else ""
    return f"{prefix}€{match.group('value')}"


def extract_units_from_text(floor_blocks: list[str]) -> list[ScrapedUnit]:
    """`floor_blocks` is one text chunk per floor/unit section of a listing
    page (however the source site groups the DOM). Each block is parsed
    independently so a multi-floor building (e.g. units on the 1st, 2nd and
    4th floor) yields one ScrapedUnit per floor rather than one flattened
    Building record (§1 row 1, §7)."""
    units: list[ScrapedUnit] = []
    floor_re = re.compile(r"(ground floor|\d+(?:st|nd|rd|th) floor)", re.IGNORECASE)
    for block in floor_blocks:
        floor_match = floor_re.search(block)
        total_area, min_area = parse_area_subdivision(block)
        units.append(
            ScrapedUnit(
                floor=floor_match.group(1) if floor_match else None,
                area_m2=total_area,
                min_divisible_area_m2=min_area,
                rent_raw=extract_price_raw(block),
                service_charge_raw=extract_price_raw(block),
                contract_term_raw="tbd",
            )
        )
    return units


def fetch_rendered_html(url: str, *, timeout_ms: int = 15_000) -> str:
    """Render `url` with the pre-installed headless Chromium. Requires
    outbound network access to the target domain — not called by the test
    suite, which exercises the pure-parsing functions above instead."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            return page.content()
        finally:
            browser.close()


def scrape(url: str) -> ScrapedListing:
    """End-to-end scrape: fetch + parse. Network-dependent; see
    fetch_rendered_html. Downstream AI normalization (§8) and the QA pass
    (§8) should run on the returned ScrapedListing before it becomes stored
    Building/Unit records.
    """
    html = fetch_rendered_html(url)
    # A production implementation would use BeautifulSoup (per §21) to select
    # DOM sections per floor/unit; kept minimal here since real-site markup
    # varies per source and isn't available to develop against in this
    # environment.
    return ScrapedListing(
        source_url=url,
        title="",
        address=None,
        description=html[:0],  # placeholder — real DOM parsing plugs in here
    )
