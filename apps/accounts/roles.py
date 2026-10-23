"""
Roles are Django groups. This file defines the built-in ones; `python manage.py setup_roles`
creates them and sets their permissions (safe to run again after editing this file).

The "Dev" role is not a group: it is a superuser account, which has every permission.
New roles can also be created as groups in the admin, without touching this file.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

FOUNDER = "Fondator"
SELLER = "Vânzător"

_SELLER_PERMISSIONS = [
    "contacte.view_contact",
    "contacte.add_contact",
    "contacte.change_contact",
    "oportunitati.view_opportunity",
    "oportunitati.add_opportunity",
    "oportunitati.change_opportunity",
    "oportunitati.view_note",
    "oportunitati.add_note",
    "oportunitati.view_task",
    "oportunitati.add_task",
    "oportunitati.change_task",
    "tabere.view_camp",
    "tabere.add_camp",
    "tabere.view_task",
    "tabere.add_task",
    "tabere.change_task",
]

ROLES = {
    # Sees every contact and opportunity, assigns contacts to people and can delete;
    # cannot manage users (no admin access).
    FOUNDER: [
        *_SELLER_PERMISSIONS,
        "contacte.view_all_contacts",
        "contacte.assign_contact",
        "contacte.delete_contact",
        "oportunitati.delete_opportunity",
        "oportunitati.view_all_opportunities",
        "oportunitati.delete_task",
        "tabere.change_camp",
        "tabere.delete_camp",
        "tabere.delete_task",
    ],
    # Sees only the contacts assigned to them and the opportunities they own; cannot delete.
    SELLER: _SELLER_PERMISSIONS,
}


def team_members():
    """Active users with a role: the people an opportunity or a task can be given to."""
    return (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__isnull=False))
        .distinct()
        .order_by("first_name", "username")
    )


def sellers_and_founders():
    """Active founders and sellers, without dev accounts: the people who work contacts."""
    return (
        get_user_model()
        .objects.filter(is_active=True, is_superuser=False, groups__name__in=[FOUNDER, SELLER])
        .distinct()
        .order_by("first_name", "username")
    )


def role_label(user):
    """Name of the user's role(s), as shown in the interface."""
    if user.is_superuser:
        return "Dev"
    return ", ".join(group.name for group in user.groups.all())
