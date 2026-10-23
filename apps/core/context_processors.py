from django.conf import settings
from django.shortcuts import resolve_url

from .navigation import sidebar_items


def layout(request):
    context = {
        "site_name": settings.SITE_NAME,
        "home_url": resolve_url(settings.LOGIN_REDIRECT_URL),
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        context["sidebar_items"] = sidebar_items(request)
    return context
