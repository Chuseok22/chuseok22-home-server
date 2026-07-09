import pytest

from apps.blog.models import Category
from apps.blog.services.category import CategoryNotFoundError, get_category_by_name


@pytest.mark.django_db
def test_존재하는_소분류_이름으로_조회하면_반환된다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)

    result = get_category_by_name('waitee-app')

    assert result.id == child.id


@pytest.mark.django_db
def test_존재하는_대분류_이름으로_조회해도_반환된다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')

    result = get_category_by_name('개발')

    assert result.id == parent.id
    assert result.parent is None


@pytest.mark.django_db
def test_존재하지_않는_이름이면_CategoryNotFoundError가_발생한다() -> None:
    with pytest.raises(CategoryNotFoundError):
        get_category_by_name('없는-카테고리')
