from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.roles import ROLES


class Command(BaseCommand):
    help = (
        "Create the built-in roles (groups) and set their permissions from apps/accounts/roles.py."
    )

    def handle(self, *args, **options):
        for name, perm_names in ROLES.items():
            permissions = []
            for perm_name in perm_names:
                app_label, codename = perm_name.split(".")
                try:
                    permissions.append(
                        Permission.objects.get(content_type__app_label=app_label, codename=codename)
                    )
                except Permission.DoesNotExist as exc:
                    raise CommandError(
                        f"Unknown permission {perm_name!r} in role {name!r}"
                    ) from exc
            group, created = Group.objects.get_or_create(name=name)
            group.permissions.set(permissions)
            verb = "created" if created else "updated"
            self.stdout.write(f"Role {name!r} {verb} with {len(permissions)} permissions.")
