"""Workflow 2 (§4): paste one or more listing URLs → scrape → normalize →
store as Building/Unit records available to any future Proposal, with no
manual re-typing required.

Extraction is deliberately coarse (see
app/services/scraping/generic_scraper.py's parse_html) — title, description,
photos, and a best-effort area/price/energy-label reading of the page text,
since real per-source DOM selectors aren't developed against real sites in
this environment. Every field that couldn't be determined is stored as
"tbd"/omitted rather than blank or guessed (§7, §24), and each URL's result
is reported independently so one bad URL doesn't fail the whole batch.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building, Unit
from app.models.enums import RentPriceType, ServiceChargePriceType
from app.services.scraping.generic_scraper import scrape

router = APIRouter(prefix="/imports", tags=["imports"])

_NUMBER_RE = re.compile(r"[\d.,]+")


class ImportUrlsRequest(BaseModel):
    urls: list[str]


class ImportResult(BaseModel):
    url: str
    status: str  # "created" | "error"
    building_id: str | None = None
    title: str | None = None
    message: str | None = None


def _parse_rent(raw: str) -> tuple[RentPriceType, float | None]:
    if raw == "tbd":
        return RentPriceType.TBD, None
    match = _NUMBER_RE.search(raw)
    value = float(match.group().replace(",", "")) if match else None
    price_type = RentPriceType.FROM if raw.startswith("from") else RentPriceType.FIXED
    return price_type, value


@router.post("/urls", response_model=list[ImportResult])
def import_urls(payload: ImportUrlsRequest, db: Session = Depends(get_db)):
    results: list[ImportResult] = []

    for url in payload.urls:
        url = url.strip()
        if not url:
            continue
        try:
            listing = scrape(url)
        except Exception as e:  # network failure, timeout, missing Chromium, etc.
            results.append(ImportResult(url=url, status="error", message=str(e)))
            continue

        building = Building(
            name=listing.title or url,
            address="TBD",
            city="TBD",
            description=listing.description or None,
            photos=listing.photos,
            source_url=listing.source_url,
            energy_label=listing.energy_label,
        )
        db.add(building)
        db.flush()

        message = None
        for scraped_unit in listing.units:
            if scraped_unit.area_m2 is None:
                message = "Area could not be determined from the page — building created without a unit; add one manually."
                continue
            rent_type, rent_value = _parse_rent(scraped_unit.rent_raw)
            db.add(
                Unit(
                    building_id=building.building_id,
                    floor=scraped_unit.floor,
                    available_area_m2=scraped_unit.area_m2,
                    min_divisible_area_m2=scraped_unit.min_divisible_area_m2,
                    rent_price_type=rent_type,
                    rent_eur_per_m2_year=rent_value,
                    service_charge_price_type=ServiceChargePriceType.TBD,
                )
            )

        db.commit()
        results.append(
            ImportResult(url=url, status="created", building_id=building.building_id, title=listing.title, message=message)
        )

    return results
