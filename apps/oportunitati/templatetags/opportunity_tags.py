from django import template

register = template.Library()

# Bootstrap color per status: grey = not started, blue/orange = in progress,
# yellow = needs work, green = accepted, red = refused.
STATUS_COLORS = {
    "nou": "secondary",
    "sunat": "info",
    "raspuns": "primary",
    "in_lucru": "warning",
    "hotarat": "success",
    "refuzat": "danger",
}


@register.inclusion_tag("components/status_badge.html")
def status_badge(opportunity):
    return {
        "color": STATUS_COLORS.get(opportunity.status, "secondary"),
        "label": opportunity.get_status_display(),
    }
