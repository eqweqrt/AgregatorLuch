# catalog/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Позволяет получать элемент словаря по ключу в шаблоне."""
    return dictionary.get(key)