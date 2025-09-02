from django import template

register = template.Library()

@register.filter
def percentage(value, total):
    """Calculate percentage of value from total"""
    try:
        if total and total > 0:
            return round((value / total) * 100, 1)
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def safe_divide(value, divisor):
    """Safely divide value by divisor, return 0 if division fails"""
    try:
        if divisor and divisor > 0:
            return value / divisor
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0



