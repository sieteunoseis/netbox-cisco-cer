"""Client for the Cisco Emergency Responder (CER) Conventional ERL REST API.

Endpoint: https://<cer>/cerappservices/service/cerl
  GET    -> all Conventional ERLs (no filtering; ?erlName= is ignored by CER)
  POST   -> insert   {"ConventionalERL": {...}}
  PUT    -> update   {"ConventionalERL": {...}} (full body)
  DELETE -> ?erlName=<name>

Quirks:
  - Failures come back as HTTP 200 with {"status": "Failure", "message": ...}
  - A single ERL is returned as an object, several as a list
  - CER only negotiates legacy TLS ciphers (needs SECLEVEL=0 on OpenSSL 3)
  - ELIN must be unique per ERL; ALI Comments max 30 characters
  - National E911 ERLs are not exposed by this API
  - JSON GET drops the last character of RoutePattern (#911 -> #91); stored value is correct.
    Real patterns are read from the XML export (/cerappservices/export/conventionalerl/info).
  - Onsite alert IDs come back space-padded, and as a string when there is only one
"""

import logging
import ssl
import xml.etree.ElementTree as ET

import requests
import urllib3
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

CACHE_KEY = "netbox_cisco_cer_conventional_erls"

ALI_FIELDS = [
    "HouseNumber",
    "HouseNumberSuffix",
    "StreetName",
    "PrefixDirectional",
    "StreetSuffix",
    "PostDirectional",
    "CommunityName",
    "State",
    "MainNPA",
    "CustomerName",
    "COS",
    "TOS",
    "Exchange",
    "MainTelNum",
    "OrderNumber",
    "CountyID",
    "CompanyID",
    "ZipCode",
    "ZipCodeExt",
    "CustomerCode",
    "Comments",
    "Longitude",
    "Latitude",
    "Elevation",
    "TARCode",
    "Location",
    "ProvReserved",
]


class CERError(Exception):
    """Raised when CER rejects a request or cannot be reached."""


class _LegacyTLSAdapter(HTTPAdapter):
    """HTTPS adapter allowing CER's legacy cipher suites."""

    def __init__(self, verify_ssl, *args, **kwargs):
        self._verify_ssl = verify_ssl
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=0")
        if not self._verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _as_list(value):
    if not value:
        return []
    return value if isinstance(value, list) else [value]


class CERClient:
    """Minimal Conventional ERL client."""

    def __init__(self, host, username, password, timeout=30, cache_timeout=60, verify_ssl=False):
        self.base_url = f"https://{host}/cerappservices/service/cerl"
        self.export_url = f"https://{host}/cerappservices/export/conventionalerl/info"
        self.timeout = timeout
        self.cache_timeout = cache_timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self.session.mount("https://", _LegacyTLSAdapter(verify_ssl))
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _request(self, method, **kwargs):
        try:
            response = self.session.request(
                method, self.base_url, timeout=self.timeout, verify=self.verify_ssl, **kwargs
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            raise CERError("CER request timed out")
        except requests.RequestException as e:
            raise CERError(f"CER request failed: {e}")
        except ValueError:
            raise CERError("CER returned a non-JSON response")
        if str(data.get("status", "")).lower() != "success":
            raise CERError(data.get("message") or "CER reported a failure with no message")
        return data

    def _export_elins(self):
        """ERL name -> [(route_pattern, elin)] from the XML export (untruncated route patterns)."""
        try:
            response = self.session.get(
                self.export_url, timeout=self.timeout, verify=self.verify_ssl, headers={"Accept": "text/xml"}
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (requests.RequestException, ET.ParseError) as e:
            logger.warning(f"CER ERL export failed, route patterns may be truncated: {e}")
            return {}
        result = {}
        for node in root.iter("ERLDetails"):
            name = (node.findtext("ERLName") or "").strip()
            pairs = []
            for item in (node.findtext("ELINSettings") or "").replace(",", ";").split(";"):
                if "--" in item:
                    pattern, elin = item.strip().split("--", 1)
                    pairs.append((pattern.strip(), elin.strip()))
            result[name] = pairs
        return result

    def list_erls(self, use_cache=True):
        """Return all Conventional ERLs as a list of dicts (normalized)."""
        if use_cache:
            cached = cache.get(CACHE_KEY)
            if cached is not None:
                return cached
        data = self._request("GET")
        exported = self._export_elins()
        details = data.get("ConventionalERLDetails") or {}
        erls = []
        for raw in _as_list(details.get("ConventionalERL")):
            name = raw.get("ERLName", "")
            elins = [
                {"route_pattern": e.get("RoutePattern", ""), "elin": e.get("ELIN", "")}
                for e in _as_list((raw.get("ELINSettings") or {}).get("ELINDetails"))
            ]
            real = {elin: pattern for pattern, elin in exported.get(name, [])}
            for e in elins:
                e["route_pattern"] = real.get(e["elin"], e["route_pattern"])
            onsite = _as_list((raw.get("OnsiteAlertSettings") or {}).get("OnsiteAlertID"))
            erls.append(
                {
                    "name": name,
                    "description": raw.get("Description", ""),
                    "time_zone": raw.get("TimeZone", ""),
                    "elins": elins,
                    "onsite_alerts": [o.strip() for o in onsite if o and o.strip()],
                    "ali": raw.get("ALIDetails") or {},
                }
            )
        cache.set(CACHE_KEY, erls, self.cache_timeout)
        return erls

    def get_erl(self, name):
        for erl in self.list_erls():
            if erl["name"] == name:
                return erl
        return None

    def save_erl(self, payload, exists):
        """Insert (POST) or update (PUT) a Conventional ERL. Returns CER's message."""
        data = self._request("PUT" if exists else "POST", json=payload)
        cache.delete(CACHE_KEY)
        return data.get("message", "")


def admin_url():
    """Link to the configured CER's admin web UI, or "" if not configured."""
    host = settings.PLUGINS_CONFIG.get("netbox_cisco_cer", {}).get("cer_host", "")
    return f"https://{host}/ceradmin/servlet/CERAdminServlet" if host else ""


def get_client():
    """Build a client from PLUGINS_CONFIG, or return None if not configured."""
    cfg = settings.PLUGINS_CONFIG.get("netbox_cisco_cer", {})
    if not cfg.get("cer_host") or not cfg.get("cer_username"):
        logger.warning("netbox_cisco_cer: cer_host / cer_username not configured")
        return None
    return CERClient(
        host=cfg["cer_host"],
        username=cfg["cer_username"],
        password=cfg.get("cer_password", ""),
        timeout=cfg.get("timeout", 30),
        cache_timeout=cfg.get("cache_timeout", 60),
        verify_ssl=cfg.get("verify_ssl", False),
    )
