"""Filtersets for NetBox Cisco CER plugin."""

import django_filters
from dcim.models import Site
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet

from .models import ERL, ERLStatusChoices


class ERLFilterSet(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(queryset=Site.objects.all(), label="Site (ID)")
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="site__slug", queryset=Site.objects.all(), to_field_name="slug", label="Site (slug)"
    )
    status = django_filters.MultipleChoiceFilter(choices=ERLStatusChoices)

    class Meta:
        model = ERL
        fields = ["id", "name", "elin", "status", "state", "zip_code"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(elin__icontains=value)
            | Q(street_name__icontains=value)
            | Q(location__icontains=value)
            | Q(site__name__icontains=value)
        )
