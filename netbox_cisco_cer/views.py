"""Views for NetBox Cisco CER plugin."""

import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from dcim.models import Site
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from netbox.views import generic
from utilities.views import ViewTab, register_model_view

from . import geocode
from .address import address_key, ali_to_fields, format_address, parse_address
from .cer_client import CERError, get_client
from .filtersets import ERLFilterSet
from .forms import ERLFilterForm, ERLForm, ERLImportForm
from .models import ERL, ERLStatusChoices
from .tables import ERLTable

logger = logging.getLogger(__name__)


def _plugin_cfg():
    return settings.PLUGINS_CONFIG.get("netbox_cisco_cer", {})


#
# ERL CRUD
#


class ERLListView(generic.ObjectListView):
    queryset = ERL.objects.select_related("site").prefetch_related("tags")
    table = ERLTable
    filterset = ERLFilterSet
    filterset_form = ERLFilterForm


class ERLView(generic.ObjectView):
    queryset = ERL.objects.select_related("site")

    def get_extra_context(self, request, instance):
        state, error, _ = _cer_state_for([instance])
        return {"cer": state.get(instance.pk), "cer_error": error}


class ERLEditView(generic.ObjectEditView):
    queryset = ERL.objects.all()
    form = ERLForm


class ERLDeleteView(generic.ObjectDeleteView):
    queryset = ERL.objects.all()


class ERLBulkImportView(generic.BulkImportView):
    queryset = ERL.objects.all()
    model_form = ERLImportForm


class ERLBulkDeleteView(generic.BulkDeleteView):
    queryset = ERL.objects.all()
    filterset = ERLFilterSet
    table = ERLTable


#
# CER helpers
#


def _fetch_cer_erls():
    """Return (erls, error). erls is None when CER is unreachable/unconfigured."""
    client = get_client()
    if client is None:
        return None, "Cisco CER is not configured (cer_host / cer_username in PLUGINS_CONFIG)"
    try:
        return client.list_erls(), None
    except CERError as e:
        logger.error(f"CER list failed: {e}")
        return None, str(e)


def _cer_state_for(records):
    """Return (state, error, erls); state maps record pk -> CER comparison dict."""
    erls, error = _fetch_cer_erls()
    if erls is None:
        return {}, error, None
    by_name = {e["name"]: e for e in erls}
    state = {}
    for rec in records:
        cer = by_name.get(rec.name)
        state[rec.pk] = {
            "present": cer is not None,
            "address_match": cer is not None
            and address_key(ali_to_fields(cer["ali"])) == address_key(rec.address_fields),
            "cer": cer,
            "cer_address": format_address(ali_to_fields(cer["ali"])) if cer else "",
            "cer_elin": ", ".join(x["elin"] for x in cer["elins"]) if cer else "",
        }
    return state, None, erls


def _new_erl_url(site):
    """Add-ERL URL prefilled from the Site's physical address and plugin defaults."""
    cfg = _plugin_cfg()
    params = {
        "site": site.pk,
        "name": site.name,
        "description": f"NetBox site {site.name}",
        "route_pattern": cfg.get("default_route_pattern", ""),
        "time_zone": str(site.time_zone) if site.time_zone else cfg.get("default_time_zone", ""),
        "cos": cfg.get("default_cos", ""),
        "tos": cfg.get("default_tos", ""),
        "customer_name": cfg.get("default_customer_name", ""),
        "company_id": cfg.get("default_company_id", ""),
        "customer_code": cfg.get("default_customer_code", ""),
        "location": site.name,
        "return_url": reverse("dcim:site_cisco_cer", args=[site.pk]),
    }
    params.update(parse_address(site.physical_address))
    return reverse("plugins:netbox_cisco_cer:erl_add") + "?" + urlencode({k: v for k, v in params.items() if v})


#
# Site tab
#


@register_model_view(Site, "cisco_cer", path="cisco-cer")
class SiteCERView(generic.ObjectView):
    queryset = Site.objects.all()
    template_name = "netbox_cisco_cer/site_tab.html"
    tab = ViewTab(label="Cisco CER", weight=9008, permission="netbox_cisco_cer.view_erl", hide_if_empty=False)

    def get(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        records = list(ERL.objects.filter(site=site))
        state, cer_error, erls = _cer_state_for(records)

        site_fields = parse_address(site.physical_address)
        site_key = address_key(site_fields)
        query = request.GET.get("q", "").strip()

        candidates = []
        if erls:
            linked = set(ERL.objects.values_list("name", flat=True))
            for erl in erls:
                if erl["name"] in linked or erl["name"] == "Default":
                    continue
                fields = ali_to_fields(erl["ali"])
                address = format_address(fields)
                haystack = " ".join([erl["name"], erl["description"], address, fields["location"]]).lower()
                match = site_key[0] != "" and address_key(fields) == site_key
                if query and query.lower() not in haystack:
                    continue
                if not query and not match:
                    continue
                candidates.append(
                    {
                        "name": erl["name"],
                        "address": address,
                        "location": fields["location"],
                        "elin": ", ".join(x["elin"] for x in erl["elins"]),
                        "match": match,
                    }
                )
            candidates.sort(key=lambda c: (not c["match"], c["name"]))

        # Address lookup: shown when the Site has no address, or on request (?lookup=1)
        show_lookup = not site.physical_address or request.GET.get("lookup") == "1"
        addr_query = request.GET.get("addr_q", "").strip()
        addr_results, addr_errors = geocode.lookup(addr_query) if show_lookup and addr_query else ([], [])
        if show_lookup and not addr_query:
            addr_query = " ".join(p for p in [site.description or site.name, site.facility] if p)

        rows = [{"record": r, "cer": state.get(r.pk)} for r in records]
        return render(
            request,
            self.template_name,
            {
                "object": site,
                "tab": self.tab,
                "rows": rows,
                "cer_error": cer_error,
                "candidates": candidates,
                "match_count": sum(1 for c in candidates if c["match"]),
                "query": query,
                "site_address": format_address(site_fields),
                "new_erl_url": _new_erl_url(site),
                "show_lookup": show_lookup,
                "addr_query": addr_query,
                "addr_searched": bool(request.GET.get("addr_q", "").strip()),
                "addr_results": addr_results,
                "addr_errors": addr_errors,
            },
        )


class SiteAddressView(PermissionRequiredMixin, View):
    """Save a looked-up address (and coordinates) onto the Site."""

    permission_required = "dcim.change_site"

    def post(self, request, site_pk):
        site = get_object_or_404(Site, pk=site_pk)
        return_url = reverse("dcim:site_cisco_cer", args=[site.pk])
        address = request.POST.get("physical_address", "").strip()
        if not address:
            messages.error(request, "No address selected.")
            return redirect(return_url)
        site.snapshot()
        site.physical_address = address[:200]
        for field in ("latitude", "longitude"):
            value = request.POST.get(field, "").strip()
            if value:
                try:
                    setattr(site, field, Decimal(value).quantize(Decimal("0.000001")))
                except InvalidOperation:
                    pass
        try:
            site.full_clean()
        except ValidationError as e:
            messages.error(request, f"Could not save address on {site}: {e}")
            return redirect(return_url)
        site.save()
        messages.success(request, f"Saved address on {site}: {site.physical_address}")
        return redirect(return_url)


#
# Actions
#


class ERLPushView(PermissionRequiredMixin, View):
    """Create or update the ERL in CER from the NetBox record."""

    permission_required = "netbox_cisco_cer.change_erl"

    def post(self, request, pk):
        erl = get_object_or_404(ERL, pk=pk)
        return_url = request.POST.get("return_url") or erl.get_absolute_url()
        if erl.status == ERLStatusChoices.STATUS_OFF_PREMISES:
            messages.error(request, f"ERL {erl} is Off-Premises; the CER Conventional ERL API can't manage it.")
            return redirect(return_url)
        client = get_client()
        if client is None:
            messages.error(request, "Cisco CER is not configured.")
            return redirect(return_url)
        erl.snapshot()
        try:
            current = client.get_erl(erl.name)
            # ELIN may have been added in the CER UI; keep it rather than wiping it on update
            if current and not erl.elin and current["elins"]:
                erl.elin = current["elins"][0]["elin"]
                erl.route_pattern = current["elins"][0]["route_pattern"]
            # Same for onsite alerts added in the CER UI
            if current and not erl.onsite_alerts and current["onsite_alerts"]:
                erl.onsite_alerts = ", ".join(current["onsite_alerts"])
            message = client.save_erl(erl.to_cer_payload(), exists=current is not None)
        except CERError as e:
            messages.error(request, f"CER rejected ERL {erl}: {e}")
            return redirect(return_url)
        erl.status = ERLStatusChoices.STATUS_IN_CER
        erl.last_pushed = timezone.now()
        erl.save()
        messages.success(request, message or f"ERL {erl} saved to CER.")
        if not erl.elin:
            messages.warning(
                request, f"ERL {erl} has no ELIN. Add one in CER (or here) before running the National E911 migration."
            )
        return redirect(return_url)


class ERLLinkView(PermissionRequiredMixin, View):
    """Create NetBox ERL records from existing CER Conventional ERLs (one or many erl_name values)."""

    permission_required = "netbox_cisco_cer.add_erl"

    def post(self, request, site_pk):
        site = get_object_or_404(Site, pk=site_pk)
        names = [n for n in request.POST.getlist("erl_name") if n]
        return_url = reverse("dcim:site_cisco_cer", args=[site.pk])
        client = get_client()
        if client is None:
            messages.error(request, "Cisco CER is not configured.")
            return redirect(return_url)
        try:
            by_name = {e["name"]: e for e in client.list_erls()}
        except CERError as e:
            messages.error(request, f"CER lookup failed: {e}")
            return redirect(return_url)

        linked, problems = [], []
        already = set(ERL.objects.filter(name__in=names).values_list("name", flat=True))
        for name in names:
            cer = by_name.get(name)
            if cer is None:
                problems.append(f"'{name}' is not in CER's Conventional ERL list")
                continue
            if name in already:
                problems.append(f"'{name}' is already linked in NetBox")
                continue
            elin = cer["elins"][0] if cer["elins"] else {"elin": "", "route_pattern": ""}
            erl = ERL(
                site=site,
                name=name,
                status=ERLStatusChoices.STATUS_IN_CER,
                description=cer["description"][:200],
                elin=elin["elin"],
                route_pattern=elin["route_pattern"],
                time_zone=cer["time_zone"],
                onsite_alerts=", ".join(cer["onsite_alerts"]),
                **ali_to_fields(cer["ali"]),
            )
            try:
                erl.full_clean()
            except ValidationError as e:
                problems.append(f"'{name}' does not fit the NetBox record: {e}")
                continue
            erl.save()
            linked.append(name)

        if linked:
            messages.success(request, f"Linked {len(linked)} CER ERL(s) to {site}: {', '.join(linked)}")
        for problem in problems:
            messages.warning(request, problem)
        if not names:
            messages.error(request, "No ERL selected.")
        return redirect(return_url)
