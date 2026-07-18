"""§11 Maps — generated once per Neighbourhood, not once per Unit (§5.4).

Static-map URL builders for Google Maps / Mapbox. Both require an API key
(GOOGLE_MAPS_API_KEY / MAPBOX_ACCESS_TOKEN) to actually resolve; this module
builds the correct request shape and is provider-agnostic at the call site,
so wiring in real credentials is a config change, not a rewrite.
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

from app.models import Building, Neighbourhood


def location_map_url(building: Building) -> str | None:
    if building.latitude is None or building.longitude is None:
        return None
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    params = {
        "center": f"{building.latitude},{building.longitude}",
        "zoom": "15",
        "size": "640x400",
        "markers": f"color:red|{building.latitude},{building.longitude}",
    }
    if api_key:
        params["key"] = api_key
    return f"https://maps.googleapis.com/maps/api/staticmap?{urlencode(params)}"


def walking_radius_map_url(building: Building, radius_m: int = 800) -> str | None:
    if building.latitude is None or building.longitude is None:
        return None
    api_key = os.environ.get("MAPBOX_ACCESS_TOKEN")
    token_part = api_key or "REPLACE_WITH_MAPBOX_ACCESS_TOKEN"
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/light-v11/static/"
        f"{building.longitude},{building.latitude},14,0/640x400"
        f"?access_token={token_part}&radius={radius_m}"
    )


def points_of_interest(neighbourhood: Neighbourhood) -> list[dict]:
    """Sourced from the Neighbourhood record so this is computed once per
    area rather than re-derived per unit (§11)."""
    return [
        {"category": a.get("category"), "name": a.get("name"), "walking_time_min": a.get("walking_time_min")}
        for a in (neighbourhood.nearby_amenities or [])
    ]


def public_transport_map(neighbourhood: Neighbourhood) -> list[dict]:
    return list(neighbourhood.public_transport or [])
