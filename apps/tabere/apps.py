from django.apps import AppConfig

from apps.core.navigation import MenuItem


class TabereConfig(AppConfig):
    name = "apps.tabere"
    label = "tabere"
    verbose_name = "Tabere"
    menu_items = (
        MenuItem(
            label="Tabere",
            url_name="tabere:list",
            icon="bi-backpack",
            order=40,
            permission="tabere.view_camp",
        ),
    )
