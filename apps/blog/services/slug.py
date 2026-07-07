from django.db import models
from django.utils.text import slugify


def generate_unique_slug(model: type[models.Model], text: str) -> str:
    """제목·이름으로부터 유일한 슬러그를 생성한다. 한글 등 유니코드 문자를 그대로 유지한다."""
    base_slug = slugify(text, allow_unicode=True) or 'item'
    slug = base_slug
    counter = 2
    while model.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug
