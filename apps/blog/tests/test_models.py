import pytest

from apps.blog.models import Post


@pytest.mark.django_db
def test_post_생성시_기본값_확인() -> None:
    post = Post.objects.create(
        title='첫 포스트',
        slug='first-post',
        content='# 안녕하세요',
    )

    assert post.is_published is False
    assert post.tags == []
    assert str(post) == '첫 포스트'


@pytest.mark.django_db
def test_post_정렬은_published_at_역순() -> None:
    from django.utils import timezone

    older = Post.objects.create(
        title='오래된 글', slug='older', content='...',
        is_published=True, published_at=timezone.now() - timezone.timedelta(days=1),
    )
    newer = Post.objects.create(
        title='최신 글', slug='newer', content='...',
        is_published=True, published_at=timezone.now(),
    )

    assert list(Post.objects.all()) == [newer, older]
