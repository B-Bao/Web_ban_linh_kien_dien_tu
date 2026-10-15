from django import template

register = template.Library()


@register.filter
def vnd(value):
    """1500000 -> '1.500.000 ₫'"""
    try:
        return f"{int(value):,}".replace(",", ".") + " ₫"
    except (TypeError, ValueError):
        return value


@register.filter
def stars(value):
    try:
        n = max(0, min(5, int(round(float(value)))))
    except (TypeError, ValueError):
        n = 0
    return "★" * n + "☆" * (5 - n)
