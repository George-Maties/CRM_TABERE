from django import template

from apps.accounts.roles import role_label

register = template.Library()


@register.filter
def display_name(user):
    """Full name, or the username when the name is empty."""
    if user is None:
        return "—"
    return user.get_full_name() or user.get_username()


@register.filter
def display_names(users):
    """Names joined the Romanian way: "Ana", "Ana și Ion", "Ana, Ion și Vlad"."""
    names = [display_name(user) for user in users]
    if len(names) > 1:
        return f"{', '.join(names[:-1])} și {names[-1]}"
    return names[0] if names else ""


@register.filter
def role(user):
    """The user's role, as shown in the interface ("Fondator", "Vânzător")."""
    return role_label(user)


@register.filter
def initials(user):
    """Two letters for an avatar: "AP" for Ana Popescu, "P" for username paula."""
    if user is None:
        return "?"
    if user.first_name or user.last_name:
        return f"{user.first_name[:1]}{user.last_name[:1]}".upper()
    return user.get_username()[:1].upper()


@register.simple_tag(takes_context=True)
def query_with(context, **changes):
    """The current query string with some parameters replaced (None removes one).
    Keeps search and filters when moving between pages or tabs."""
    params = context["request"].GET.copy()
    params.pop("page", None)
    for key, value in changes.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"
