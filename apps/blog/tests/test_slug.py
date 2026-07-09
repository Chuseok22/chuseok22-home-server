from datetime import datetime
from unittest.mock import patch

import pytest

from apps.blog.models import Post
from apps.blog.services.slug import generate_unique_slug


@pytest.mark.django_db
def test_영문_제목으로_슬러그를_생성한다() -> None:
    slug = generate_unique_slug(Post, 'My First Post')

    assert slug == 'my-first-post'


@pytest.mark.django_db
def test_중복된_영문_슬러그는_접미사가_붙는다() -> None:
    Post.objects.create(title='Duplicate Post', slug='duplicate-post', content='...')

    slug = generate_unique_slug(Post, 'Duplicate Post')

    assert slug == 'duplicate-post-2'


@pytest.mark.django_db
@patch('apps.blog.services.slug.timezone.now')
def test_순한글_제목이면_오늘_날짜로_슬러그를_생성한다(mock_now) -> None:
    mock_now.return_value = datetime(2026, 7, 9)

    slug = generate_unique_slug(Post, '첫 블로그 글')

    assert slug == '20260709'


@pytest.mark.django_db
@patch('apps.blog.services.slug.timezone.now')
def test_날짜_폴백_슬러그가_중복되면_접미사가_붙는다(mock_now) -> None:
    mock_now.return_value = datetime(2026, 7, 9)
    Post.objects.create(title='첫 글', slug='20260709', content='...')

    slug = generate_unique_slug(Post, '두번째 글')

    assert slug == '20260709-2'
