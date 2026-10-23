from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from django.views.debug import default_urlconf

from apps.core.views import health

admin.site.site_header = settings.SITE_NAME
admin.site.site_title = settings.SITE_NAME

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("", include("apps.accounts.urls")),
    path("wall/", include("apps.wall.urls")),
    path("oportunitati/", include("apps.oportunitati.urls")),
    path("contacte/", include("apps.contacte.urls")),
    path("tabere/", include("apps.tabere.urls")),
    path("cazari/", include("apps.cazari.urls")),
]

if settings.DEBUG:
    # Django's "install worked" rocket page, until the CRM has its own home page.
    urlpatterns.append(path("", login_not_required(default_urlconf)))
