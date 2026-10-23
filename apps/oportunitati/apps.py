from django.apps import AppConfig

from apps.core.navigation import MenuItem


class OportunitatiConfig(AppConfig):
    name = "apps.oportunitati"
    label = "oportunitati"
    verbose_name = "Oportunități"
    menu_items = (
        MenuItem(
            label="Oportunități",
            url_name="oportunitati:list",
            icon="bi-briefcase",
            order=20,
            permission="oportunitati.view_opportunity",
        ),
    )
