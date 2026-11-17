"""API views for NetBox Cisco CER plugin."""

from netbox.api.viewsets import NetBoxModelViewSet

from ..filtersets import ERLFilterSet
from ..models import ERL
from .serializers import ERLSerializer


class ERLViewSet(NetBoxModelViewSet):
    queryset = ERL.objects.select_related("site").prefetch_related("tags")
    serializer_class = ERLSerializer
    filterset_class = ERLFilterSet
