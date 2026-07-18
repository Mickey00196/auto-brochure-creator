"""Workflow 2 (§4) import router tests. The network/browser call (`scrape`)
is monkeypatched out so these stay fast and deterministic — live scraping's
actual parsing logic is covered by tests/test_scraping.py's pure-function
tests against raw HTML instead.
"""
from __future__ import annotations

from app.routers import imports as imports_router
from app.services.scraping.base import ScrapedListing, ScrapedUnit


def _fake_listing_with_unit(url: str) -> ScrapedListing:
    return ScrapedListing(
        source_url=url,
        title="Test Building",
        address=None,
        description="A test listing",
        photos=["https://example.test/photo.jpg"],
        units=[
            ScrapedUnit(
                floor=None, area_m2=250, min_divisible_area_m2=None,
                rent_raw="€200", service_charge_raw="tbd", contract_term_raw="tbd",
            )
        ],
        energy_label="A",
    )


def _fake_listing_without_area(url: str) -> ScrapedListing:
    return ScrapedListing(
        source_url=url,
        title="No Area Building",
        address=None,
        description="",
        units=[
            ScrapedUnit(
                floor=None, area_m2=None, min_divisible_area_m2=None,
                rent_raw="tbd", service_charge_raw="tbd", contract_term_raw="tbd",
            )
        ],
    )


def test_import_creates_building_and_unit(client, monkeypatch):
    monkeypatch.setattr(imports_router, "scrape", _fake_listing_with_unit)
    r = client.post("/imports/urls", json={"urls": ["https://example.test/listing-1"]})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["status"] == "created"
    assert body[0]["title"] == "Test Building"

    buildings = client.get("/buildings").json()
    match = next(b for b in buildings if b["building_id"] == body[0]["building_id"])
    assert len(match["units"]) == 1
    assert match["units"][0]["available_area_m2"] == 250
    assert match["units"][0]["rent_eur_per_m2_year"] == 200


def test_import_without_area_creates_building_but_no_unit(client, monkeypatch):
    """§7/§24: an unresolved area must not be guessed (e.g. defaulted to 0) —
    skip the Unit and say so, rather than store a fabricated figure."""
    monkeypatch.setattr(imports_router, "scrape", _fake_listing_without_area)
    r = client.post("/imports/urls", json={"urls": ["https://example.test/listing-2"]})
    body = r.json()
    assert body[0]["status"] == "created"
    assert body[0]["message"] is not None

    buildings = client.get("/buildings").json()
    match = next(b for b in buildings if b["building_id"] == body[0]["building_id"])
    assert len(match["units"]) == 0


def test_import_reports_error_per_url_without_failing_batch(client, monkeypatch):
    def _raising_scrape(url: str) -> ScrapedListing:
        if "bad" in url:
            raise RuntimeError("network unreachable")
        return _fake_listing_with_unit(url)

    monkeypatch.setattr(imports_router, "scrape", _raising_scrape)
    r = client.post("/imports/urls", json={"urls": ["https://example.test/good", "https://example.test/bad-url"]})
    body = r.json()
    assert body[0]["status"] == "created"
    assert body[1]["status"] == "error"
    assert "network unreachable" in body[1]["message"]
