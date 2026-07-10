import pytest
from django.utils import timezone

from apps.blog.models import Category, Post
from apps.blog.services.category import (
    CategoryNotFoundError,
    filter_published_posts_by_category_slug,
    get_category_by_name,
    get_category_sidebar_items,
)


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


@pytest.mark.django_db
def test_공개_글이_있는_카테고리만_사이드바에_노출된다() -> None:
    with_post = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(
        title='글', slug='post-1', content='본문', category=with_post,
        is_published=True, published_at=timezone.now(),
    )
    Category.objects.create(name='빈 카테고리', slug='empty')

    items = get_category_sidebar_items()

    slugs = [item.slug for item in items]
    assert 'dev' in slugs
    assert 'empty' not in slugs


@pytest.mark.django_db
def test_대분류_개수는_소분류_글까지_합산한다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='대분류 글', slug='p1', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )
    Post.objects.create(
        title='소분류 글', slug='p2', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    items = get_category_sidebar_items()

    dev_item = next(item for item in items if item.slug == 'dev')
    assert dev_item.post_count == 2


@pytest.mark.django_db
def test_소분류_개수는_직속_글만_센다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='대분류 글', slug='p1', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )
    Post.objects.create(
        title='소분류 글', slug='p2', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    items = get_category_sidebar_items()

    dev_item = next(item for item in items if item.slug == 'dev')
    child_item = next(item for item in dev_item.children if item.slug == 'waitee-app')
    assert child_item.post_count == 1


@pytest.mark.django_db
def test_대분류만_글이_있고_소분류는_글이_없어도_대분류가_노출된다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='대분류 글', slug='p1', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )

    items = get_category_sidebar_items()

    dev_item = next(item for item in items if item.slug == 'dev')
    assert dev_item.post_count == 1
    assert dev_item.children == ()


@pytest.mark.django_db
def test_대분류에_직속_글이_없어도_소분류_글이_있으면_대분류가_합산_개수로_노출된다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='소분류 글 1', slug='p1', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )
    Post.objects.create(
        title='소분류 글 2', slug='p2', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    items = get_category_sidebar_items()

    dev_item = next(item for item in items if item.slug == 'dev')
    assert dev_item.post_count == 2
    assert [child.slug for child in dev_item.children] == ['waitee-app']


@pytest.mark.django_db
def test_비공개_글은_사이드바_개수에서_제외된다() -> None:
    category = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(title='비공개 글', slug='draft', content='본문', category=category, is_published=False)

    items = get_category_sidebar_items()

    assert items == []


@pytest.mark.django_db
def test_대분류_slug로_필터링하면_소분류_글도_포함된다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    post1 = Post.objects.create(
        title='대분류 글', slug='p1', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )
    post2 = Post.objects.create(
        title='소분류 글', slug='p2', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    result = filter_published_posts_by_category_slug('dev')

    assert set(result.values_list('id', flat=True)) == {post1.id, post2.id}


@pytest.mark.django_db
def test_소분류_slug로_필터링하면_해당_소분류_글만_반환한다() -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='대분류 글', slug='p1', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )
    post2 = Post.objects.create(
        title='소분류 글', slug='p2', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    result = filter_published_posts_by_category_slug('waitee-app')

    assert list(result.values_list('id', flat=True)) == [post2.id]


@pytest.mark.django_db
def test_존재하지_않는_slug면_빈_결과를_반환한다() -> None:
    Post.objects.create(title='글', slug='p1', content='본문', is_published=True, published_at=timezone.now())

    result = filter_published_posts_by_category_slug('없는-슬러그')

    assert list(result) == []


@pytest.mark.django_db
def test_category_slug가_없으면_전체_공개_글을_반환한다() -> None:
    Post.objects.create(title='글', slug='p1', content='본문', is_published=True, published_at=timezone.now())
    Post.objects.create(title='비공개', slug='p2', content='본문', is_published=False)

    result = filter_published_posts_by_category_slug(None)

    assert result.count() == 1
