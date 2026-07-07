from apps.blog.models import Category
from apps.blog.services.slug import generate_unique_slug

_DEV_CATEGORY_NAME = '개발'


def get_or_create_dev_category(repo_name: str) -> Category:
    """ingest API 전용: '개발' 대분류 아래에 저장소명을 소분류로 자동 생성한다."""
    parent, _ = Category.objects.get_or_create(
        name=_DEV_CATEGORY_NAME,
        defaults={'slug': generate_unique_slug(Category, _DEV_CATEGORY_NAME)},
    )
    child, _ = Category.objects.get_or_create(
        name=repo_name,
        defaults={
            'slug': generate_unique_slug(Category, repo_name),
            'parent': parent,
        },
    )
    return child
