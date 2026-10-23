from django import template

register = template.Library()

# Bootstrap color per status: blue = being worked on, green = won, red = lost.
STATUS_COLORS = {
    "potential": "primary",
    "castigata": "success",
    "pierduta": "danger",
}

# Icon of a status change in the history, by the status it led to
STATUS_ICONS = {
    "potential": "arrow-repeat",
    "castigata": "trophy",
    "pierduta": "x-lg",
}


@register.filter
def status_color(status):
    return STATUS_COLORS.get(status, "secondary")


@register.filter
def status_icon(status):
    return STATUS_ICONS.get(status, "arrow-left-right")


@register.inclusion_tag("components/status_badge.html")
def status_badge(opportunity):
    return {
        "color": STATUS_COLORS.get(opportunity.status, "secondary"),
        "label": opportunity.get_status_display(),
    }
