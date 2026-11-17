"""URL configuration for NetBox Cisco CER plugin."""

from django.urls import path
from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from . import models, views

urlpatterns = [
    path("erls/", views.ERLListView.as_view(), name="erl_list"),
    path("erls/add/", views.ERLEditView.as_view(), name="erl_add"),
    path("erls/import/", views.ERLBulkImportView.as_view(), name="erl_bulk_import"),
    path("erls/delete/", views.ERLBulkDeleteView.as_view(), name="erl_bulk_delete"),
    path("erls/<int:pk>/", views.ERLView.as_view(), name="erl"),
    path("erls/<int:pk>/edit/", views.ERLEditView.as_view(), name="erl_edit"),
    path("erls/<int:pk>/delete/", views.ERLDeleteView.as_view(), name="erl_delete"),
    path("erls/<int:pk>/push/", views.ERLPushView.as_view(), name="erl_push"),
    path(
        "erls/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="erl_changelog",
        kwargs={"model": models.ERL},
    ),
    path(
        "erls/<int:pk>/journal/",
        ObjectJournalView.as_view(),
        name="erl_journal",
        kwargs={"model": models.ERL},
    ),
    path("sites/<int:site_pk>/link/", views.ERLLinkView.as_view(), name="erl_link"),
    path("sites/<int:site_pk>/address/", views.SiteAddressView.as_view(), name="site_address"),
]
