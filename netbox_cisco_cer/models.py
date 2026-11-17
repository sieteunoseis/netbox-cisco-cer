"""Models for NetBox Cisco CER plugin."""

from dcim.models import Site
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from utilities.choices import ChoiceSet

from .address import format_address


class ERLStatusChoices(ChoiceSet):
    key = "ERL.status"

    STATUS_PLANNED = "planned"
    STATUS_IN_CER = "in_cer"
    STATUS_MIGRATED = "migrated"
    STATUS_OFF_PREMISES = "off_premises"

    CHOICES = [
        (STATUS_PLANNED, "Planned", "blue"),
        (STATUS_IN_CER, "In CER (Conventional)", "green"),
        (STATUS_MIGRATED, "Migrated (National E911)", "purple"),
        (STATUS_OFF_PREMISES, "Off-Premises ERL", "orange"),
    ]


class ERL(NetBoxModel):
    """A Cisco CER Conventional ERL tied to a NetBox Site."""

    site = models.ForeignKey(to=Site, on_delete=models.CASCADE, related_name="cer_erls")
    name = models.CharField(max_length=100, unique=True, verbose_name="ERL name")
    status = models.CharField(max_length=30, choices=ERLStatusChoices, default=ERLStatusChoices.STATUS_PLANNED)
    description = models.CharField(max_length=200, blank=True)

    # ELIN settings (CER requires a unique ELIN per ERL)
    route_pattern = models.CharField(max_length=50, blank=True)
    elin = models.CharField(max_length=20, blank=True, verbose_name="ELIN")
    time_zone = models.CharField(max_length=64, blank=True)
    onsite_alerts = models.CharField(
        max_length=200, blank=True, help_text="Comma-separated CER Onsite Alert IDs, e.g. PublicSafety, Telecom"
    )

    # ALI address
    house_number = models.CharField(max_length=10, blank=True)
    house_number_suffix = models.CharField(max_length=4, blank=True)
    prefix_directional = models.CharField(max_length=2, blank=True)
    street_name = models.CharField(max_length=60, blank=True)
    street_suffix = models.CharField(max_length=4, blank=True)
    post_directional = models.CharField(max_length=2, blank=True)
    community_name = models.CharField(max_length=32, blank=True, verbose_name="City")
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=5, blank=True)
    zip_code_ext = models.CharField(max_length=4, blank=True)
    location = models.CharField(max_length=60, blank=True, help_text="ALI Location (building / floor / room)")

    # ALI service info
    cos = models.CharField(max_length=50, blank=True, verbose_name="Class of service")
    tos = models.CharField(max_length=50, blank=True, verbose_name="Type of service")
    customer_name = models.CharField(max_length=32, blank=True)
    company_id = models.CharField(max_length=10, blank=True, verbose_name="Company ID")
    customer_code = models.CharField(max_length=10, blank=True)

    last_pushed = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("site", "name")
        verbose_name = "ERL"
        verbose_name_plural = "ERLs"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_cisco_cer:erl", args=[self.pk])

    def get_status_color(self):
        return ERLStatusChoices.colors.get(self.status)

    @property
    def address_fields(self):
        return {
            f: getattr(self, f)
            for f in (
                "house_number",
                "house_number_suffix",
                "prefix_directional",
                "street_name",
                "street_suffix",
                "post_directional",
                "community_name",
                "state",
                "zip_code",
            )
        }

    @property
    def formatted_address(self):
        return format_address(self.address_fields)

    @property
    def onsite_alert_list(self):
        """Per-ERL onsite alerts plus the plugin's always-attached defaults (order kept, no duplicates)."""
        from django.conf import settings

        defaults = settings.PLUGINS_CONFIG.get("netbox_cisco_cer", {}).get("default_onsite_alerts", [])
        ids = [*defaults, *(p.strip() for p in self.onsite_alerts.split(","))]
        return list(dict.fromkeys(i for i in ids if i))

    def to_cer_payload(self):
        """Build the CER insert/update request body."""
        ali = {
            "HouseNumber": self.house_number,
            "HouseNumberSuffix": self.house_number_suffix,
            "StreetName": self.street_name,
            "PrefixDirectional": self.prefix_directional,
            "StreetSuffix": self.street_suffix,
            "PostDirectional": self.post_directional,
            "CommunityName": self.community_name,
            "State": self.state,
            "MainNPA": "",
            "CustomerName": self.customer_name,
            "COS": self.cos,
            "TOS": self.tos,
            "Exchange": "",
            "MainTelNum": "",
            "OrderNumber": "",
            "CountyID": "",
            "CompanyID": self.company_id,
            "ZipCode": self.zip_code,
            "ZipCodeExt": self.zip_code_ext,
            "CustomerCode": self.customer_code,
            # CER limits Comments to 30 characters; used as a back-reference to NetBox
            "Comments": f"NetBox site {self.site_id}"[:30],
            "Longitude": "",
            "Latitude": "",
            "Elevation": "",
            "TARCode": "",
            "Location": self.location,
            "ProvReserved": "",
        }
        erl = {
            "ERLName": self.name,
            "Description": self.description,
            "TestERL": False,
            "TimeZone": self.time_zone,
            "ALIDetails": ali,
        }
        if self.onsite_alert_list:
            erl["OnsiteAlertSettings"] = {"OnsiteAlertID": self.onsite_alert_list}
        if self.elin:
            erl["ELINSettings"] = {"ELINDetails": [{"RoutePattern": self.route_pattern, "ELIN": self.elin}]}
        return {"ConventionalERL": erl}
