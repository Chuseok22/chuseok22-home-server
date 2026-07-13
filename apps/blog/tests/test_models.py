import pytest

from django.core.exceptions import ValidationError

from apps.blog.models import Category, Post, Tag


@pytest.mark.django_db
def test_post_생성시_기본값_확인() -> None:
    post = Post.objects.create(
        title='첫 포스트',
        slug='first-post',
        content='# 안녕하세요',
    )

    assert post.is_published is False
    assert list(post.tags.all()) == []
    assert post.views_count == 0
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


@pytest.mark.django_db
def test_카테고리는_자기_자신을_부모로_지정할_수_없다() -> None:
    category = Category.objects.create(name='개발', slug='dev')
    category.parent = category

    with pytest.raises(ValidationError):
        category.save()


@pytest.mark.django_db
def test_카테고리_save는_ORM_경로에서도_3단계_중첩을_거부한다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)

    with pytest.raises(ValidationError):
        Category.objects.create(name='세부', slug='detail', parent=child)


@pytest.mark.django_db
def test_대소문자만_다른_태그_이름은_생성할_수_없다() -> None:
    Tag.objects.create(name='Django', slug='django')

    with pytest.raises(ValidationError):
        Tag(name='django', slug='django-2').save()


@pytest.mark.django_db
def test_태그는_최초_입력_케이스_그대로_저장된다() -> None:
    tag = Tag.objects.create(name='React', slug='react')

    assert tag.name == 'React'
    assert str(tag) == 'React'
