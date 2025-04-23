# catalog/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Позволяет получать элемент словаря по ключу в шаблоне."""
    return dictionary.get(key)

@register.filter(name='get_nested_item')
def get_nested_item(item_data, key):
     """
     Получает элемент из словаря item_data по заданному key.
     Используется после фильтра get_item.
     Пример: {{ selection|get_item:model.id|get_nested_item:'quantity' }}
     """
     if isinstance(item_data, dict) and key in item_data:
          return item_data.get(key)
     return None # Возвращаем None, если input не словарь или ключ не найден