"""Tables for NetBox Cisco CER plugin."""

import django_tables2 as tables
from netbox.tables import ChoiceFieldColumn, NetBoxTable, columns

from .models import ERL


class ERLTable(NetBoxTable):
    name = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    status = ChoiceFieldColumn()
    formatted_address = tables.Column(verbose_name="Address", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_cisco_cer:erl_list")

    class Meta(NetBoxTable.Meta):
        model = ERL
        fields = (
            "pk",
            "id",
            "name",
            "site",
            "status",
            "elin",
            "route_pattern",
            "formatted_address",
            "location",
            "time_zone",
            "onsite_alerts",
            "last_pushed",
            "description",
            "tags",
        )
        default_columns = ("name", "site", "status", "elin", "formatted_address", "location", "last_pushed")
