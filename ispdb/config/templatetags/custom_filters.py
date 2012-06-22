#ispdb/templatetags/data_verbose.py
from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def data_verbose(boundField, attr_name="value"):
    """
    Returns field's data or it's verbose version 
    for a field with choices defined.

    Usage::

        {% load data_verbose %}
        {{form.some_field|data_verbose}}
    """
    data = boundField[attr_name]
    field = boundField
    rv = data
    if field.has_key("choices") and dict(field['choices']).get(data, ''):
        rv = dict(field["choices"]).get(data, "")
    return rv

@register.filter
def is_undo_available(self):
    delta = timezone.now() - self.deleted_datetime
    if delta.days > 0:
        return False
    return True
