from django import template

register = template.Library()


@register.filter
def split(value, sep):
    try:
        return value.split(sep)[0]
    except IndexError:
        return value
