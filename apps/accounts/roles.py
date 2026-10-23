"""
Roles are Django groups. This file defines the built-in ones; `python manage.py setup_roles`
creates them and sets their permissions (safe to run again after editing this file).

The "Dev" role is not a group: it is a superuser account, which has every permission.
New roles can also be created as groups in the admin, without touching this file.
"""

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
]

ROLES = {
    # Sees every opportunity and can delete; cannot manage users (no admin access).
    FOUNDER: [
        *_SELLER_PERMISSIONS,
        "contacte.delete_contact",
        "oportunitati.delete_opportunity",
        "oportunitati.delete_task",
        "oportunitati.view_all_opportunities",
    ],
    # Sees only the opportunities they own or have a task on; cannot delete.
    SELLER: _SELLER_PERMISSIONS,
}


def role_label(user):
    """Name of the user's role(s), as shown in the interface."""
    if user.is_superuser:
        return "Dev"
    return ", ".join(group.name for group in user.groups.all())
