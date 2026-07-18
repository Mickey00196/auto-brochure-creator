"""§7 Scraping Engine — pure-function tests (no network dependency)."""
from __future__ import annotations

from app.services.scraping.generic_scraper import (
    extract_price_raw,
    extract_units_from_text,
    parse_area_subdivision,
)


def test_preserves_subdivision_instead_of_collapsing():
    """§7: "581 m², units from 150 m²" must not collapse to one figure."""
    total, min_divisible = parse_area_subdivision("581 m², units from 150 m²")
    assert total == 581
    assert min_divisible == 150


def test_parses_parenthesized_subdivision():
    total, min_divisible = parse_area_subdivision("307 m² (from 75 m²)")
    assert total == 307
    assert min_divisible == 75


def test_simple_area_has_no_subdivision():
    total, min_divisible = parse_area_subdivision("431 m²")
    assert total == 431
    assert min_divisible is None


def test_price_raw_fixed():
    assert extract_price_raw("Rent: €243 per m² per year") == "€243"


def test_price_raw_from_range():
    assert extract_price_raw("Rent: from €245 per m²") == "from €245"


def test_price_raw_missing_becomes_tbd_not_blank():
    """§7/§24: unmapped fields must be explicitly 'tbd', never blank or guessed."""
    assert extract_price_raw("Rent: TBD") == "tbd"
    assert extract_price_raw("No pricing information on this page") == "tbd"


def test_extract_units_from_multi_floor_building():
    """§1 row 1: Moermanskkade 600 has separately available units on the 1st,
    2nd and 4th floor — each floor block should yield its own ScrapedUnit."""
    blocks = [
        "1st floor — 620 m², from €240 per m², service charge €58",
        "2nd floor — 410 m², price TBD",
        "4th floor — 307 m² (from 75 m²), price TBD",
    ]
    units = extract_units_from_text(blocks)
    assert len(units) == 3
    assert units[0].floor == "1st floor"
    assert units[2].min_divisible_area_m2 == 75
