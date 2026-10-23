from django.contrib import admin
from django.urls import path

from apps.core.views import health

admin.site.site_header = "CRM Tabere"
admin.site.site_title = "CRM Tabere"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
