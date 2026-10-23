from django import template

register = template.Library()

# Bootstrap color per status: grey = not started, blue/orange = in progress,
# yellow = needs work, green = won, red = lost.
STATUS_COLORS = {
    "nou": "secondary",
    "sunat": "info",
    "raspuns": "primary",
    "in_lucru": "warning",
    "castigata": "success",
    "pierduta": "danger",
}


@register.inclusion_tag("components/status_badge.html")
def status_badge(opportunity):
    return {
        "color": STATUS_COLORS.get(opportunity.status, "secondary"),
        "label": opportunity.get_status_display(),
    }
