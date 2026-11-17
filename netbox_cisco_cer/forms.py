"""Forms for NetBox Cisco CER plugin."""

from dcim.models import Site
from django import forms
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm, NetBoxModelImportForm
from utilities.forms.fields import (
    CommentField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

from .models import ERL, ERLStatusChoices

ERL_FIELDS = [
    "site",
    "name",
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
    "comments",
    "tags",
]


class ERLForm(NetBoxModelForm):
    site = DynamicModelChoiceField(queryset=Site.objects.all())
    comments = CommentField()

    fieldsets = (
        FieldSet("site", "name", "status", "description", name="ERL"),
        FieldSet("elin", "route_pattern", "time_zone", "onsite_alerts", name="ELIN / Alerts"),
        FieldSet(
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
            name="ALI Address",
        ),
        FieldSet("cos", "tos", "customer_name", "company_id", "customer_code", name="ALI Service"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = ERL
        fields = ERL_FIELDS
        help_texts = {
            "elin": "Optional to push; required before CER National E911 migration. Must be unique per ERL",
            "street_suffix": "USPS abbreviation, e.g. DR, AVE, RD",
        }


class ERLFilterForm(NetBoxModelFilterSetForm):
    model = ERL

    site_id = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Site")
    status = forms.MultipleChoiceField(choices=ERLStatusChoices, required=False)
    tag = TagFilterField(model)


class ERLImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(queryset=Site.objects.all(), to_field_name="name")

    class Meta:
        model = ERL
        fields = [f for f in ERL_FIELDS if f != "tags"]
