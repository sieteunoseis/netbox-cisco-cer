"""
NetBox Cisco CER Plugin

Manage Cisco Emergency Responder (CER) Conventional ERLs from NetBox Site addresses.
ERL records live in NetBox, are pushed to CER via its REST API, and can be linked
to Conventional ERLs that already exist in CER.
"""

from netbox.plugins import PluginConfig

__version__ = "0.2.0"


class CiscoCERConfig(PluginConfig):
    """Plugin configuration for NetBox Cisco CER integration."""

    name = "netbox_cisco_cer"
    verbose_name = "Cisco CER"
    description = "Manage Cisco Emergency Responder Conventional ERLs from NetBox Sites"
    version = __version__
    author = "Jeremy Worden"
    author_email = "jeremy.worden@gmail.com"
    base_url = "cisco-cer"
    min_version = "4.7.4"
    max_version = "5.99"

    required_settings = []

    default_settings = {
        # CER publisher, e.g. "cer.example.com" (https is assumed)
        "cer_host": "",
        "cer_username": "",
        "cer_password": "",
        "timeout": 30,
        # Seconds to cache the Conventional ERL list
        "cache_timeout": 60,
        "verify_ssl": False,
        # Site tab position among other plugin tabs (lower = further left)
        "tab_weight": 9008,
        # Defaults applied to new ERL records (all editable per ERL)
        "default_route_pattern": "#911",
        # Onsite Alert IDs always attached to every ERL pushed to CER, e.g. ["PublicSafety"]
        "default_onsite_alerts": [],
        "default_time_zone": "America/Los_Angeles",
        "default_cos": "Business PBX",
        "default_tos": "FX in 911 area",
        "default_customer_name": "",
        "default_company_id": "",
        "default_customer_code": "",
        # Address lookup for Sites without an address (US Census + OpenStreetMap Nominatim)
        "geocoder_countrycodes": "us",
        "geocoder_user_agent": "",  # defaults to "netbox-cisco-cer/<version>"
    }


config = CiscoCERConfig
