"""API URL configuration for NetBox Cisco CER plugin."""

from netbox.api.routers import NetBoxRouter

from . import views

router = NetBoxRouter()
router.register("erls", views.ERLViewSet)

urlpatterns = router.urls
