# from django.template.defaultfilters import floatformat
from django.template import Library

register = Library()


def formatted_float(value):
    return str(value).replace(",", ".")


def formatted_int(value):
    return str(value).split(",")[0].split(".")[0]


register.filter("formatted_float", formatted_float)
register.filter("formatted_int", formatted_int)
