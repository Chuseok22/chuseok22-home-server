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
    if child.parent_id != parent.id:
        # Category.name이 전역 unique라, 저장소명과 같은 이름의 카테고리가
        # 이미 다른 상위 카테고리 아래 존재하면 엉뚱한 카테고리를 반환하게 된다.
        # 잘못된 분류로 조용히 이어지지 않도록 명시적으로 실패시킨다.
        raise ValueError(f"카테고리 '{repo_name}'이 이미 다른 상위 카테고리 아래에 존재합니다.")
    return child
