"""§16 Comparison Generator.

The reference brochure never showed a combined €/m²/year or an estimated
annual cost — readers had to do that math themselves across 7 different
rent/service-charge pairs (§1 row 7). This module computes both, and is the
single place both the Comparison Generator output and the PPTX "Comparison"
slide (§14) pull from — so the number a client sees is always computed the
same way.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models import AddOn, Unit


@dataclass
class ComparisonRow:
    unit_id: str
    building_name: str
    address: str
    floor: str | None
    available_area_m2: float
    rent_eur_per_m2_year: float | None
    rent_price_type: str
    service_charge_eur_per_m2_year: float | None
    service_charge_price_type: str
    all_in_rate_eur_per_m2_year: float | None
    estimated_annual_cost_eur: float | None
    is_tbd: bool
    energy_label: str | None
    contract_term: str | None
    availability: str | None
    parking_price_range: str | None

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "building_name": self.building_name,
            "address": self.address,
            "floor": self.floor,
            "available_area_m2": self.available_area_m2,
            "rent_eur_per_m2_year": self.rent_eur_per_m2_year,
            "rent_price_type": self.rent_price_type,
            "service_charge_eur_per_m2_year": self.service_charge_eur_per_m2_year,
            "service_charge_price_type": self.service_charge_price_type,
            "all_in_rate_eur_per_m2_year": self.all_in_rate_eur_per_m2_year,
            "estimated_annual_cost_eur": self.estimated_annual_cost_eur,
            "is_tbd": self.is_tbd,
            "energy_label": self.energy_label,
            "contract_term": self.contract_term,
            "availability": self.availability,
            "parking_price_range": self.parking_price_range,
        }


def _parking_price_range(addons: list[AddOn]) -> str | None:
    parking = [a for a in addons if "parking" in a.name.lower()]
    if not parking:
        return None
    prices = sorted(a.price for a in parking)
    # price_unit already reads like "EUR / space / year" — swap the leading
    # "EUR" for a "€" prefix on the number instead of stacking both symbols.
    unit_suffix = parking[0].price_unit.split("/", 1)[-1].strip()
    if prices[0] == prices[-1]:
        return f"€{prices[0]:,.0f} / {unit_suffix}"
    return f"€{prices[0]:,.0f}–€{prices[-1]:,.0f} / {unit_suffix}"


def build_comparison_row(unit: Unit, addons: list[AddOn] | None = None) -> ComparisonRow:
    addons = addons or (unit.addons or [])
    rent = unit.rent_eur_per_m2_year
    service = unit.service_charge_eur_per_m2_year
    is_tbd = rent is None or service is None or unit.rent_price_type == "tbd" or unit.service_charge_price_type == "tbd"

    all_in_rate = None if is_tbd else round(rent + service, 2)
    annual_cost = None if is_tbd else round(all_in_rate * unit.available_area_m2, 2)

    return ComparisonRow(
        unit_id=unit.unit_id,
        building_name=unit.building.name,
        address=unit.building.address,
        floor=unit.floor,
        available_area_m2=unit.available_area_m2,
        rent_eur_per_m2_year=rent,
        rent_price_type=unit.rent_price_type.value if hasattr(unit.rent_price_type, "value") else unit.rent_price_type,
        service_charge_eur_per_m2_year=service,
        service_charge_price_type=(
            unit.service_charge_price_type.value
            if hasattr(unit.service_charge_price_type, "value")
            else unit.service_charge_price_type
        ),
        all_in_rate_eur_per_m2_year=all_in_rate,
        estimated_annual_cost_eur=annual_cost,
        is_tbd=is_tbd,
        energy_label=unit.building.energy_label,
        contract_term=unit.contract_term,
        availability=unit.availability,
        parking_price_range=_parking_price_range(addons),
    )


def build_comparison_table(units: list[Unit]) -> list[ComparisonRow]:
    """Default sort: ready (non-TBD) rows first by all-in rate ascending, TBD rows last."""
    rows = [build_comparison_row(unit) for unit in units]
    rows.sort(
        key=lambda r: (r.is_tbd, r.all_in_rate_eur_per_m2_year if r.all_in_rate_eur_per_m2_year is not None else float("inf"))
    )
    return rows
