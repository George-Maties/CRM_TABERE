from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.debug import default_urlconf

from apps.core.views import health

admin.site.site_header = "CRM Tabere"
admin.site.site_title = "CRM Tabere"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]

if settings.DEBUG:
    # Django's "install worked" rocket page, until the CRM has its own home page.
    urlpatterns.append(path("", default_urlconf))
