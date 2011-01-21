#ispdb/templatetags/data_verbose.py
from django import template

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
    data = boundField["value"]
    field = boundField
    rv = data
    if field.has_key("choices") and dict(field['choices']).get(data, ''):
        rv = dict(field["choices"]).get(data, "")
    return rv