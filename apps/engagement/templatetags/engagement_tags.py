from django import template
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model

register = template.Library()


@register.filter
def content_type_app_label(obj: Model) -> str:
    return ContentType.objects.get_for_model(obj).app_label


@register.filter
def content_type_model(obj: Model) -> str:
    return ContentType.objects.get_for_model(obj).model
