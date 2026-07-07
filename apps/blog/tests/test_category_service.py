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


@pytest.mark.django_db
def test_저장소명과_같은_이름의_카테고리가_다른_상위에_있으면_예외가_발생한다() -> None:
    other_parent = Category.objects.create(name='일상', slug='daily')
    Category.objects.create(name='waitee-app', slug='waitee-app', parent=other_parent)

    with pytest.raises(ValueError):
        get_or_create_dev_category('waitee-app')
