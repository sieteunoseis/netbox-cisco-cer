"""API serializers for NetBox Cisco CER plugin."""

from dcim.api.serializers import SiteSerializer
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from ..models import ERL


class ERLSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_cisco_cer-api:erl-detail")
    site = SiteSerializer(nested=True)

    class Meta:
        model = ERL
        fields = [
            "id",
            "url",
            "display",
            "site",
            "name",
            "status",
            "description",
            "route_pattern",
            "elin",
            "time_zone",
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
            "last_pushed",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ["id", "url", "display", "name", "elin"]
