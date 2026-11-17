"""Tables for NetBox Cisco CER plugin."""

import django_tables2 as tables
from netbox.tables import ChoiceFieldColumn, NetBoxTable, columns

from .models import ELIN, ERL


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
            "last_seen_export",
            "erl_type",
            "description",
            "tags",
        )
        default_columns = ("name", "site", "status", "elin", "formatted_address", "location", "last_pushed")


class ELINTable(NetBoxTable):
    number = tables.Column(linkify=True)
    status = ChoiceFieldColumn()
    erl = tables.Column(linkify=True, orderable=False, verbose_name="ERL record")
    tags = columns.TagColumn(url_name="plugins:netbox_cisco_cer:elin_list")

    class Meta(NetBoxTable.Meta):
        model = ELIN
        fields = ("pk", "id", "number", "status", "building_name", "erl_name", "erl", "note", "tags")
        default_columns = ("number", "status", "building_name", "erl_name", "erl", "note")
