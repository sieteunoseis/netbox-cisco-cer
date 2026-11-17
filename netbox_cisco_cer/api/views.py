"""API views for NetBox Cisco CER plugin."""

from netbox.api.viewsets import NetBoxModelViewSet

from ..filtersets import ELINFilterSet, ERLFilterSet
from ..models import ELIN, ERL
from .serializers import ELINSerializer, ERLSerializer


class ERLViewSet(NetBoxModelViewSet):
    queryset = ERL.objects.select_related("site").prefetch_related("tags")
    serializer_class = ERLSerializer
    filterset_class = ERLFilterSet


class ELINViewSet(NetBoxModelViewSet):
    queryset = ELIN.objects.prefetch_related("tags")
    serializer_class = ELINSerializer
    filterset_class = ELINFilterSet
