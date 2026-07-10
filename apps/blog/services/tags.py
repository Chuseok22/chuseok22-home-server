from django.db import models

from apps.blog.models import Tag
from apps.blog.services.slug import generate_unique_slug


def get_or_create_tags(raw_names: list[str], tag_model: type[models.Model] = Tag) -> list[Tag]:
    """이름 목록을 대소문자 무시로 기존 Tag에 매핑하거나 새로 생성한다.
    공백 문자열은 제외하고, 같은 호출 내 중복 이름은 한 번만 반환한다.
    tag_model은 마이그레이션의 historical model에서도 이 함수를 재사용할 수 있도록 주입받는다."""
    tags: list[Tag] = []
    seen_ids: set[int] = set()
    for raw_name in raw_names:
        name = raw_name.strip()
        if not name:
            continue
        tag = tag_model.objects.filter(name__iexact=name).first()
        if tag is None:
            tag = tag_model.objects.create(name=name, slug=generate_unique_slug(tag_model, name))
        if tag.id not in seen_ids:
            seen_ids.add(tag.id)
            tags.append(tag)
    return tags
