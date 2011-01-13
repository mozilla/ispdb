#ispdb/templatetags/data_verbose.py
from django import template
import sys

register = template.Library()

@register.filter
def data_verbose(boundField):
    """
    Returns field's data or it's verbose version 
    for a field with choices defined.

    Usage::

        {% load data_verbose %}
        {{form.some_field|data_verbose}}
    """
    data = boundField['value']
    field = boundField
    return field.has_key('choices') and dict(field['choices']).get(data, '') or data