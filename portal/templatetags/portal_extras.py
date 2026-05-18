from django import template

register = template.Library()


@register.filter
def status_badge(value):
    mapping = {
        "ready": "ok",
        "processing": "warn",
        "pending": "neutral",
        "failed": "bad",
    }
    return mapping.get(str(value), "neutral")
