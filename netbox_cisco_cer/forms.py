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

from .models import ELIN, ERL, ELINStatusChoices, ERLStatusChoices, next_available_elin

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
    "ali_comments",
    "comments",
    "tags",
]


class ERLForm(NetBoxModelForm):
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
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
        FieldSet("cos", "tos", "customer_name", "company_id", "customer_code", "ali_comments", name="ALI Service"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = ERL
        fields = ERL_FIELDS
        help_texts = {
            "elin": "Optional to push; required before CER National E911 migration. Must be unique per ERL",
            "street_suffix": "USPS abbreviation, e.g. DR, AVE, RD",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # New ERLs always start as Planned; Push/Link set "In CER". Status is editable afterwards.
        if not self.instance.pk:
            self.fields["status"].disabled = True
            self.fields["status"].initial = ERLStatusChoices.STATUS_PLANNED
            self.fields["status"].help_text = "New ERLs start as Planned; pushing or linking sets In CER"
        suggestion = next_available_elin()
        if suggestion:
            self.fields["elin"].help_text += f". Next available in the ELIN pool: {suggestion.number}"

    def clean_elin(self):
        elin = "".join(ch for ch in (self.cleaned_data.get("elin") or "") if ch.isdigit())
        if elin:
            clash = ERL.objects.filter(elin=elin).exclude(pk=self.instance.pk).first()
            if clash:
                raise forms.ValidationError(f"ELIN {elin} is already used by ERL {clash.name}")
        return elin


class ERLFilterForm(NetBoxModelFilterSetForm):
    model = ERL

    site_id = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Site")
    has_site = forms.NullBooleanField(
        required=False, label="Has site", widget=forms.Select(choices=[("", "---"), ("true", "Yes"), ("false", "No")])
    )
    status = forms.MultipleChoiceField(choices=ERLStatusChoices, required=False)
    tag = TagFilterField(model)


class ERLImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(queryset=Site.objects.all(), to_field_name="name", required=False)

    class Meta:
        model = ERL
        fields = [f for f in ERL_FIELDS if f != "tags"]


class ELINForm(NetBoxModelForm):
    comments = CommentField()

    fieldsets = (FieldSet("number", "status", "building_name", "erl_name", "note", "tags", name="ELIN"),)

    class Meta:
        model = ELIN
        fields = ["number", "status", "building_name", "erl_name", "note", "comments", "tags"]


class ELINFilterForm(NetBoxModelFilterSetForm):
    model = ELIN

    status = forms.MultipleChoiceField(choices=ELINStatusChoices, required=False)
    tag = TagFilterField(model)


class CERImportForm(forms.Form):
    KIND_CHOICES = [
        ("national_erls", "CER National ERL export (CSV)"),
        ("elin_sheet", "ELIN tracking sheet (CSV: Phone Number, Building Name, ERL Name, Status, Note)"),
    ]

    kind = forms.ChoiceField(choices=KIND_CHOICES, label="File type")
    csv_file = forms.FileField(label="CSV file")
    dry_run = forms.BooleanField(
        required=False, initial=True, label="Dry run", help_text="Preview the changes without saving anything"
    )
