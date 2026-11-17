"""Split a free-text US street address into CER ALI fields and compare addresses."""

import re

DIRECTIONALS = {
    "N": "N",
    "NORTH": "N",
    "S": "S",
    "SOUTH": "S",
    "E": "E",
    "EAST": "E",
    "W": "W",
    "WEST": "W",
    "NE": "NE",
    "NORTHEAST": "NE",
    "NW": "NW",
    "NORTHWEST": "NW",
    "SE": "SE",
    "SOUTHEAST": "SE",
    "SW": "SW",
    "SOUTHWEST": "SW",
}

# USPS Publication 28 street suffix abbreviations (common subset)
STREET_SUFFIXES = {
    "ALLEY": "ALY",
    "AVENUE": "AVE",
    "AVE": "AVE",
    "BOULEVARD": "BLVD",
    "BLVD": "BLVD",
    "CIRCLE": "CIR",
    "CIR": "CIR",
    "COURT": "CT",
    "CT": "CT",
    "DRIVE": "DR",
    "DR": "DR",
    "HIGHWAY": "HWY",
    "HWY": "HWY",
    "LANE": "LN",
    "LN": "LN",
    "LOOP": "LOOP",
    "PARKWAY": "PKWY",
    "PKWY": "PKWY",
    "PLACE": "PL",
    "PL": "PL",
    "ROAD": "RD",
    "RD": "RD",
    "SQUARE": "SQ",
    "SQ": "SQ",
    "STREET": "ST",
    "ST": "ST",
    "TERRACE": "TER",
    "TER": "TER",
    "TRAIL": "TRL",
    "TRL": "TRL",
    "WAY": "WAY",
}

_LINE_RE = re.compile(r"^\s*(?P<house>\d+)(?P<suffix>[A-Z])?\s+(?P<street>.+?)\s*$", re.IGNORECASE)
_CITY_RE = re.compile(r"^\s*(?P<city>.+?)\s*,?\s+(?P<state>[A-Z]{2})\s+(?P<zip>\d{5})(?:-(?P<zip4>\d{4}))?\s*$", re.I)


def parse_address(text):
    """Best-effort parse of "579 SW Campus Drive, Portland, OR 97239".

    Returns a dict of model field names; unparsed parts are left blank for the user to fill in.
    """
    result = {
        "house_number": "",
        "house_number_suffix": "",
        "prefix_directional": "",
        "street_name": "",
        "street_suffix": "",
        "post_directional": "",
        "community_name": "",
        "state": "",
        "zip_code": "",
        "zip_code_ext": "",
    }
    if not text:
        return result

    lines = [p.strip() for p in re.split(r"[\n,]", text) if p.strip()]
    if not lines:
        return result

    # City / state / zip: try the last one or two comma-separated parts
    tail = None
    if len(lines) >= 3:
        tail = f"{lines[-2]} {lines[-1]}"
        street_parts = lines[:-2]
    elif len(lines) == 2:
        tail = lines[-1]
        street_parts = lines[:-1]
    else:
        street_parts = lines
    if tail:
        m = _CITY_RE.match(tail)
        if m:
            result["community_name"] = m.group("city").strip()
            result["state"] = m.group("state").upper()
            result["zip_code"] = m.group("zip")
            result["zip_code_ext"] = m.group("zip4") or ""

    m = _LINE_RE.match(street_parts[0])
    if not m:
        result["street_name"] = street_parts[0]
        return result

    result["house_number"] = m.group("house")
    result["house_number_suffix"] = (m.group("suffix") or "").upper()
    words = m.group("street").split()

    if len(words) > 1 and words[0].upper().rstrip(".") in DIRECTIONALS:
        result["prefix_directional"] = DIRECTIONALS[words.pop(0).upper().rstrip(".")]
    if len(words) > 1 and words[-1].upper().rstrip(".") in DIRECTIONALS:
        result["post_directional"] = DIRECTIONALS[words.pop().upper().rstrip(".")]
    if len(words) > 1 and words[-1].upper().rstrip(".") in STREET_SUFFIXES:
        result["street_suffix"] = STREET_SUFFIXES[words.pop().upper().rstrip(".")]
    result["street_name"] = " ".join(words)
    return result


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def address_key(fields):
    """Comparable key from a dict of model-style address fields."""
    suffix = _norm(fields.get("street_suffix"))
    return (
        _norm(fields.get("house_number")),
        _norm(fields.get("house_number_suffix")),
        DIRECTIONALS.get(_norm(fields.get("prefix_directional")), _norm(fields.get("prefix_directional"))),
        _norm(fields.get("street_name")),
        STREET_SUFFIXES.get(suffix, suffix),
        DIRECTIONALS.get(_norm(fields.get("post_directional")), _norm(fields.get("post_directional"))),
        _norm(fields.get("community_name")),
        _norm(fields.get("state")),
        _norm(fields.get("zip_code")),
    )


def ali_to_fields(ali):
    """Map CER ALIDetails keys to model field names."""
    return {
        "house_number": ali.get("HouseNumber", ""),
        "house_number_suffix": ali.get("HouseNumberSuffix", ""),
        "prefix_directional": ali.get("PrefixDirectional", ""),
        "street_name": ali.get("StreetName", ""),
        "street_suffix": ali.get("StreetSuffix", ""),
        "post_directional": ali.get("PostDirectional", ""),
        "community_name": ali.get("CommunityName", ""),
        "state": ali.get("State", ""),
        "zip_code": ali.get("ZipCode", ""),
        "zip_code_ext": ali.get("ZipCodeExt", ""),
        "location": ali.get("Location", ""),
        "cos": ali.get("COS", ""),
        "tos": ali.get("TOS", ""),
        "customer_name": ali.get("CustomerName", ""),
        "company_id": ali.get("CompanyID", ""),
        "customer_code": ali.get("CustomerCode", ""),
    }


def format_address(fields):
    street = " ".join(
        p
        for p in [
            f"{fields.get('house_number', '')}{fields.get('house_number_suffix', '')}",
            fields.get("prefix_directional", ""),
            fields.get("street_name", ""),
            fields.get("street_suffix", ""),
            fields.get("post_directional", ""),
        ]
        if p
    )
    city = ", ".join(p for p in [fields.get("community_name", ""), fields.get("state", "")] if p)
    return " ".join(p for p in [street + ("," if street and city else ""), city, fields.get("zip_code", "")] if p)
