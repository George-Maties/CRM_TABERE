from django.apps import AppConfig

from apps.core.navigation import MenuItem


class WallConfig(AppConfig):
    name = "apps.wall"
    label = "wall"
    verbose_name = "Wall"
    menu_items = (MenuItem(label="Wall", url_name="wall:index", icon="bi-newspaper", order=10),)
