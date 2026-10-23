from django.apps import AppConfig

from apps.core.navigation import MenuItem


class ContacteConfig(AppConfig):
    name = "apps.contacte"
    label = "contacte"
    verbose_name = "Contacte"
    menu_items = (
        MenuItem(
            label="Contacte", url_name="contacte:welcome", icon="bi-person-lines-fill", order=30
        ),
    )
