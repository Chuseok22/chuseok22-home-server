import pytest
from django.utils import timezone

from apps.blog.models import Category, Post
from apps.blog.services.post_editor import update_post_content


@pytest.mark.django_db
def test_update_post_content은_제목_요약_본문만_갱신한다() -> None:
    category = Category.objects.create(name='개발', slug='dev')
    post = Post.objects.create(
        title='원래 제목', slug='original-slug', summary='원래 요약', content='원래 본문',
        category=category, is_published=True, published_at=timezone.now(),
    )

    result = update_post_content(post, title='새 제목', summary='새 요약', content='새 본문')

    post.refresh_from_db()
    assert result.title == '새 제목'
    assert post.title == '새 제목'
    assert post.summary == '새 요약'
    assert post.content == '새 본문'
    # 인라인 수정 대상이 아닌 필드는 그대로 유지돼야 한다
    assert post.slug == 'original-slug'
    assert post.category_id == category.id


@pytest.mark.django_db
def test_update_post_content은_요약을_빈_문자열로_비울_수_있다() -> None:
    post = Post.objects.create(
        title='제목', slug='post-with-summary', summary='기존 요약', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    update_post_content(post, title='제목', summary='', content='본문')

    post.refresh_from_db()
    assert post.summary == ''
