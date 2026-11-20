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
    path("elins/", views.ELINListView.as_view(), name="elin_list"),
    path("elins/add/", views.ELINEditView.as_view(), name="elin_add"),
    path("elins/delete/", views.ELINBulkDeleteView.as_view(), name="elin_bulk_delete"),
    path("elins/<int:pk>/", views.ELINView.as_view(), name="elin"),
    path("elins/<int:pk>/edit/", views.ELINEditView.as_view(), name="elin_edit"),
    path("elins/<int:pk>/delete/", views.ELINDeleteView.as_view(), name="elin_delete"),
    path(
        "elins/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="elin_changelog",
        kwargs={"model": models.ELIN},
    ),
    path("import/", views.CERImportView.as_view(), name="cer_import"),
    path("import/rematch/", views.ERLRematchView.as_view(), name="erl_rematch"),
    path("sites/<int:site_pk>/link/", views.ERLLinkView.as_view(), name="erl_link"),
    path("sites/<int:site_pk>/address/", views.SiteAddressView.as_view(), name="site_address"),
]
