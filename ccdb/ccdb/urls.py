from contextlib import suppress

from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from ccdb import views

app_name = "ccdb"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/admin")),
    path("api/v1/", include("api.urls", namespace="api")),
    path(
        "downloads/invoice/<int:number>/",
        views.download_invoice,
        name="download_invoice",
    ),
]

with suppress(ImportError):
    if settings.DEBUG:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]
