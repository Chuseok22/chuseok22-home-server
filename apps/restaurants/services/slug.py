from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def generate_unique_slug(model: type[models.Model], text: str) -> str:
    """제목·이름으로부터 유일한 슬러그를 생성한다.
    영문/숫자 슬러그로 통일한다 — 한글 등 비ASCII만 있는 텍스트는 결과가 비므로,
    그런 경우 오늘 날짜(YYYYMMDD)를 기본값으로 대신 사용한다.
    """
    base_slug = slugify(text) or timezone.now().strftime('%Y%m%d')
    slug = base_slug
    counter = 2
    while model.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug
