import pytest

from django.core.exceptions import ValidationError

from apps.blog.models import Category, Post


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


@pytest.mark.django_db
def test_카테고리는_3단계_중첩이_금지된다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    grandchild = Category(name='세부', slug='detail', parent=child)

    with pytest.raises(ValidationError):
        grandchild.clean()


@pytest.mark.django_db
def test_카테고리는_최상위끼리는_중첩_제약에_걸리지_않는다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category(name='waitee-app', slug='waitee-app', parent=parent)

    child.clean()  # 예외가 발생하지 않아야 한다
