import pytest

from apps.blog.models import Post
from apps.blog.services.slug import generate_unique_slug


@pytest.mark.django_db
def test_한글_제목으로_슬러그를_생성한다() -> None:
    slug = generate_unique_slug(Post, '첫 블로그 글')

    assert slug == '첫-블로그-글'


@pytest.mark.django_db
def test_중복된_슬러그는_접미사가_붙는다() -> None:
    Post.objects.create(title='중복 글', slug='중복-글', content='...')

    slug = generate_unique_slug(Post, '중복 글')

    assert slug == '중복-글-2'


@pytest.mark.django_db
def test_슬러그로_변환할_수_없는_제목은_item으로_대체된다() -> None:
    slug = generate_unique_slug(Post, '!!!')

    assert slug == 'item'
