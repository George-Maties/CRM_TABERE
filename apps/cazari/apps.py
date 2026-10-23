from django.apps import AppConfig

from apps.core.navigation import MenuItem


class CazariConfig(AppConfig):
    name = "apps.cazari"
    label = "cazari"
    verbose_name = "Cazări"
    menu_items = (
        MenuItem(
            label="Cazări",
            url_name="cazari:list",
            icon="bi-house-door",
            order=50,
            permission="cazari.view_accommodation",
        ),
    )
