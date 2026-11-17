"""Address lookup for Sites without a physical address.

Sources (both free, no API key):
  - US Census geocoder: street addresses only, returns USPS-style components (ideal for ALI)
  - OpenStreetMap Nominatim: also finds places by name (e.g. a building); 1 req/s usage policy
Results are cached for a day to keep request volume low.
"""

import hashlib
import logging

import requests
from django.conf import settings
from django.core.cache import cache

from . import __version__
from .address import format_address, parse_address

logger = logging.getLogger(__name__)

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CACHE_SECONDS = 86400


def _cfg():
    return settings.PLUGINS_CONFIG.get("netbox_cisco_cer", {})


def _cached(source, query, fetch):
    key = "netbox_cisco_cer_geo_" + hashlib.sha1(f"{source}:{query.lower()}".encode()).hexdigest()
    hit = cache.get(key)
    if hit is not None:
        return hit
    results = fetch(query)
    cache.set(key, results, CACHE_SECONDS)
    return results


def _result(source, label, physical_address, lat, lon):
    fields = parse_address(physical_address)
    return {
        "source": source,
        "label": label,
        "physical_address": physical_address,
        "parsed": format_address(fields),
        "complete": bool(fields["house_number"] and fields["street_name"] and fields["zip_code"]),
        "latitude": round(float(lat), 6) if lat not in (None, "") else None,
        "longitude": round(float(lon), 6) if lon not in (None, "") else None,
    }


def _census(query):
    response = requests.get(
        CENSUS_URL,
        params={"address": query, "benchmark": "Public_AR_Current", "format": "json"},
        timeout=_cfg().get("timeout", 30),
    )
    response.raise_for_status()
    results = []
    for match in response.json().get("result", {}).get("addressMatches", []):
        c = match.get("addressComponents", {})
        street = " ".join(
            p
            for p in [
                c.get("preDirection", ""),
                c.get("preType", ""),
                c.get("streetName", "").title(),
                c.get("suffixType", ""),
                c.get("suffixDirection", ""),
            ]
            if p
        )
        house = match.get("matchedAddress", "").split(" ", 1)[0]
        if not house.isdigit():
            house = ""
        physical = f"{house} {street}, {c.get('city', '').title()}, {c.get('state', '')} {c.get('zip', '')}".strip()
        coords = match.get("coordinates", {})
        results.append(
            _result("US Census", match.get("matchedAddress", ""), physical, coords.get("y"), coords.get("x"))
        )
    return results


def _nominatim(query):
    cfg = _cfg()
    params = {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 8}
    if cfg.get("geocoder_countrycodes"):
        params["countrycodes"] = cfg["geocoder_countrycodes"]
    response = requests.get(
        NOMINATIM_URL,
        params=params,
        headers={"User-Agent": cfg.get("geocoder_user_agent") or f"netbox-cisco-cer/{__version__}"},
        timeout=cfg.get("timeout", 30),
    )
    response.raise_for_status()
    results = []
    for place in response.json():
        a = place.get("address", {})
        state = (a.get("ISO3166-2-lvl4") or "").replace("US-", "") or a.get("state", "")
        city = a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or ""
        street = " ".join(p for p in [a.get("house_number", ""), a.get("road", "")] if p)
        physical = ", ".join(p for p in [street, city, f"{state} {a.get('postcode', '')}".strip()] if p)
        results.append(
            _result("OpenStreetMap", place.get("display_name", ""), physical, place.get("lat"), place.get("lon"))
        )
    return results


def lookup(query):
    """Return (results, errors). Census is only queried when the text starts with a house number."""
    query = (query or "").strip()
    results, errors = [], []
    if not query:
        return results, errors
    sources = [("osm", _nominatim)]
    if query[:1].isdigit():
        sources.insert(0, ("census", _census))
    for name, fetch in sources:
        try:
            results.extend(_cached(name, query, fetch))
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"Address lookup via {name} failed: {e}")
            errors.append(f"{'US Census' if name == 'census' else 'OpenStreetMap'} lookup failed: {e}")
    # De-duplicate by parsed address, keep the first (Census before OSM)
    seen, unique = set(), []
    for r in results:
        key = r["parsed"].upper()
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique, errors
