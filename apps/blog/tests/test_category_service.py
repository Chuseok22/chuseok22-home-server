import pytest

from apps.blog.models import Category
from apps.blog.services.category import get_or_create_dev_category


@pytest.mark.django_db
def test_처음_호출하면_개발_대분류와_저장소_소분류가_함께_생성된다() -> None:
    category = get_or_create_dev_category('waitee-app')

    assert category.name == 'waitee-app'
    assert category.parent is not None
    assert category.parent.name == '개발'
    assert category.parent.parent is None


@pytest.mark.django_db
def test_같은_저장소로_다시_호출하면_기존_카테고리를_재사용한다() -> None:
    first = get_or_create_dev_category('waitee-app')
    second = get_or_create_dev_category('waitee-app')

    assert first.id == second.id
    assert Category.objects.filter(parent__isnull=True, name='개발').count() == 1
