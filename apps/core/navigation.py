from dataclasses import dataclass

from django.apps import apps
from django.urls import reverse


@dataclass(frozen=True)
class MenuItem:
    """A sidebar button. Each app declares its own in AppConfig.menu_items."""

    label: str
    url_name: str
    icon: str  # Bootstrap Icons class, e.g. "bi-people"
    order: int = 100
    permission: str | None = None  # e.g. "contacte.view_contact"; None = every user


def sidebar_items(request):
    """Menu items from all installed apps that the current user may see, sorted by order."""
    entries = []
    for app_config in apps.get_app_configs():
        for item in getattr(app_config, "menu_items", ()):
            if item.permission and not request.user.has_perm(item.permission):
                continue
            url = reverse(item.url_name)
            entries.append(
                {
                    "label": item.label,
                    "icon": item.icon,
                    "url": url,
                    "active": request.path.startswith(url),
                    "order": item.order,
                }
            )
    return sorted(entries, key=lambda entry: entry["order"])
