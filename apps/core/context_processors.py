from django.conf import settings
from django.shortcuts import resolve_url

from apps.accounts.roles import role_label

from .navigation import sidebar_items


def layout(request):
    context = {
        # Not "site_name": Django's auth views set their own (the domain) and it would win.
        "brand_name": settings.SITE_NAME,
        "home_url": resolve_url(settings.LOGIN_REDIRECT_URL),
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        context["sidebar_items"] = sidebar_items(request)
        context["role_label"] = role_label(user)
    return context
