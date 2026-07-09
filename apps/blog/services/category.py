from apps.blog.models import Category


class CategoryNotFoundError(Exception):
    """이름과 일치하는 카테고리가 없을 때 발생한다."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"카테고리 '{name}'을 찾을 수 없습니다.")


def get_category_by_name(name: str) -> Category:
    """이름으로 기존 카테고리를 조회한다. 대분류/소분류 구분 없이 그대로 사용한다."""
    try:
        return Category.objects.get(name=name)
    except Category.DoesNotExist:
        raise CategoryNotFoundError(name) from None
