import pytest

from apps.blog.models import Tag
from apps.blog.services.tags import get_or_create_tags


@pytest.mark.django_db
def test_기존_태그와_대소문자만_다르면_기존_태그를_재사용한다() -> None:
    existing = Tag.objects.create(name='Django', slug='django')

    tags = get_or_create_tags(['django'])

    assert tags == [existing]
    assert Tag.objects.count() == 1


@pytest.mark.django_db
def test_공백_문자열은_제외한다() -> None:
    tags = get_or_create_tags(['React', '  ', ''])

    assert [tag.name for tag in tags] == ['React']


@pytest.mark.django_db
def test_새로운_이름은_새_Tag를_생성한다() -> None:
    tags = get_or_create_tags(['Vue'])

    assert len(tags) == 1
    assert tags[0].name == 'Vue'
    assert tags[0].slug == 'vue'


@pytest.mark.django_db
def test_같은_호출에_중복된_이름이_있으면_한번만_반환한다() -> None:
    tags = get_or_create_tags(['Go', 'go', 'Go'])

    assert len(tags) == 1
    assert Tag.objects.count() == 1
