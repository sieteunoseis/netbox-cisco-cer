"""Import CER ERL exports into NetBox.

Accepts CER's own ERL export CSV (National E911 or Conventional; same columns, told apart by "ERL Type").
Upserts keyed on ERL name, so re-importing a newer export updates records in place.
"""

import csv
import io

from dcim.models import Site
from django.db import transaction
from django.utils import timezone

from .address import address_key, parse_address
from .models import ERL, ERLStatusChoices

# NENA class/type of service codes -> CER display names (CER's lists are these in reverse code order)
COS_CODES = {
    "0": "Business OPX",
    "1": "Residence",
    "2": "Business",
    "3": "Residence PBX",
    "4": "Business PBX",
    "5": "Centrex",
    "6": "Coin 1W out",
    "7": "Coin 2Way",
    "8": "Mobile/Wireless Phase 0",
    "9": "ResidenceOPX",
}
TOS_CODES = {
    "0": "Not FX nor Non-Pub",
    "1": "FX in 911 area",
    "2": "FX outside 911 area",
    "3": "Non-Pub",
    "4": "Non-Pub FX in 911 area",
    "5": "Non-Pub FX outside 911 area",
    "6": "Local Ported Number (LNP)",
}

ERL_COLUMNS = {"ERLName", "ELINSettings", "HouseNumber", "StreetName"}
SKIP_ERLS = {"Default"}  # every CER has one; not tied to a site

# Fields an import may overwrite (site and comments are never overwritten once set)
ERL_IMPORT_FIELDS = [
    "status",
    "description",
    "route_pattern",
    "elin",
    "time_zone",
    "onsite_alerts",
    "house_number",
    "house_number_suffix",
    "prefix_directional",
    "street_name",
    "street_suffix",
    "post_directional",
    "community_name",
    "state",
    "zip_code",
    "zip_code_ext",
    "location",
    "cos",
    "tos",
    "customer_name",
    "company_id",
    "customer_code",
    "ali_comments",
    "erl_type",
]


class ImportFormatError(Exception):
    pass


def _read_csv(data, required):
    text = data.decode("utf-8-sig") if isinstance(data, bytes) else data
    reader = csv.DictReader(io.StringIO(text))
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ImportFormatError(f"Missing column(s): {', '.join(sorted(missing))}. Is this the right file?")
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def _status_for(erl_type):
    t = erl_type.lower()
    if "national" in t:
        return ERLStatusChoices.STATUS_MIGRATED
    if "off" in t and "premis" in t:
        return ERLStatusChoices.STATUS_OFF_PREMISES
    return ERLStatusChoices.STATUS_IN_CER


def _row_to_fields(row):
    route_pattern, elin = "", ""
    first = row.get("ELINSettings", "").split(";")[0]
    if "--" in first:
        route_pattern, elin = (p.strip() for p in first.split("--", 1))
    cos, tos = row.get("Class of Service", ""), row.get("Type of Service", "")
    return {
        "status": _status_for(row.get("ERL Type", "")),
        "description": row.get("ERLNotes", "")[:200],
        "route_pattern": route_pattern,
        "elin": elin,
        "time_zone": row.get("Time Zone", ""),
        "onsite_alerts": ", ".join(a.strip() for a in row.get("OnSiteAlertSettings", "").split(";") if a.strip()),
        "house_number": row.get("HouseNumber", ""),
        "house_number_suffix": row.get("HouseNumberSuffix", ""),
        "prefix_directional": row.get("Prefix Directional", ""),
        "street_name": row.get("StreetName", ""),
        "street_suffix": row.get("Street Suffix", ""),
        "post_directional": row.get("Post Directional", ""),
        "community_name": row.get("Community Name", ""),
        "state": row.get("State", ""),
        "zip_code": row.get("ZIP Code", ""),
        "zip_code_ext": row.get("ZIP Code Ext", ""),
        "location": row.get("Location", ""),
        "cos": COS_CODES.get(cos, cos),
        "tos": TOS_CODES.get(tos, tos),
        "customer_name": row.get("Customer Name", ""),
        "company_id": row.get("Company ID", ""),
        "customer_code": row.get("Customer Code", ""),
        "ali_comments": row.get("Comments", "")[:30],
        "erl_type": row.get("ERL Type", "")[:50],
    }


class SiteMatcher:
    """Match an ERL to a Site by name prefix ("ADMN 0-2" -> site "ADMN"), then by unique street address."""

    def __init__(self):
        self.by_name = {}
        by_address = {}
        for site in Site.objects.only("id", "name", "physical_address"):
            self.by_name[site.name.upper()] = site
            if site.physical_address:
                by_address.setdefault(address_key(parse_address(site.physical_address))[:6], []).append(site)
        self.by_address = {k: v[0] for k, v in by_address.items() if len(v) == 1}

    def match(self, name, fields):
        prefix = name.split()[0].upper() if name.split() else ""
        if prefix in self.by_name:
            return self.by_name[prefix], "name"
        key = address_key(fields)[:6]
        if key[0] and key in self.by_address:
            return self.by_address[key], "address"
        return None, None


def import_cer_export(data, dry_run=True):
    """Upsert ERL records from a CER ERL export CSV. Returns a summary dict."""
    rows = _read_csv(data, ERL_COLUMNS)
    now = timezone.now()
    matcher = SiteMatcher()
    existing = {e.name: e for e in ERL.objects.all()}
    result = {"rows": len(rows), "created": [], "updated": [], "unchanged": 0, "no_site": [], "errors": []}
    seen, seen_statuses = set(), set()

    with transaction.atomic():
        for row in rows:
            name = row.get("ERLName", "")
            if not name or name in SKIP_ERLS:
                continue
            seen.add(name)
            fields = _row_to_fields(row)
            seen_statuses.add(fields["status"])
            erl = existing.get(name)
            if erl is None:
                site, how = matcher.match(name, fields)
                erl = ERL(name=name, site=site, **fields)
                action = "created"
            else:
                changed = [f for f in ERL_IMPORT_FIELDS if getattr(erl, f) != fields[f]]
                site, how = erl.site, "existing"
                if erl.site is None:
                    site, how = matcher.match(name, fields)
                    if site:
                        changed.append("site")
                if not changed:
                    result["unchanged"] += 1
                    if not dry_run:
                        ERL.objects.filter(pk=erl.pk).update(last_seen_export=now)
                    if erl.site is None:
                        result["no_site"].append(name)
                    continue
                erl.snapshot()
                for f in ERL_IMPORT_FIELDS:
                    setattr(erl, f, fields[f])
                erl.site = site
                action = "updated"
            erl.last_seen_export = now
            try:
                erl.full_clean()
            except Exception as e:  # ValidationError, reported per row
                result["errors"].append(f"{name}: {e}")
                continue
            if not dry_run:
                erl.save()
            result[action].append(name)
            if site is None:
                result["no_site"].append(name)
        if dry_run:
            transaction.set_rollback(True)

    # Only ERL types present in this file count as "missing" (a Conventional export says nothing about National ERLs)
    result["missing_from_export"] = sorted(
        e.name
        for e in existing.values()
        if e.status in seen_statuses and e.status != ERLStatusChoices.STATUS_PLANNED and e.name not in seen
    )
    return result
