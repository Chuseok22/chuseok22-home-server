import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.blog.models import Post

User = get_user_model()


@pytest.mark.django_db
def test_포스트_생성() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:post-create'), {
        'title': '테스트 포스트',
        'slug': 'test-post',
        'summary': '',
        'content': '본문 내용',
        'tags': '[]',
        'is_published': 'on',
        'published_at': '',
    })

    assert response.status_code == 200
    assert Post.objects.filter(slug='test-post', is_published=True).exists()


@pytest.mark.django_db
def test_슬러그_중복시_저장되지_않는다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    Post.objects.create(title='기존 글', slug='dup-slug', content='...')
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:post-create'), {
        'title': '새 글',
        'slug': 'dup-slug',
        'summary': '',
        'content': '내용',
        'tags': '[]',
        'published_at': '',
    })

    assert response.status_code == 200
    assert Post.objects.filter(slug='dup-slug').count() == 1


@pytest.mark.django_db
def test_포스트_수정() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    post = Post.objects.create(title='원래 제목', slug='original', content='...')
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:post-update', args=[post.pk]), {
        'title': '수정된 제목',
        'slug': 'original',
        'summary': '',
        'content': '수정된 내용',
        'tags': '[]',
        'published_at': '',
    })

    assert response.status_code == 200
    post.refresh_from_db()
    assert post.title == '수정된 제목'
    assert post.content == '수정된 내용'


@pytest.mark.django_db
def test_포스트_삭제는_POST만_허용() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    post = Post.objects.create(title='삭제 대상', slug='to-delete', content='...')
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('dashboard:post-delete', args=[post.pk]))
    assert response.status_code == 405

    response = client.post(reverse('dashboard:post-delete', args=[post.pk]))
    assert response.status_code == 200
    assert not Post.objects.filter(pk=post.pk).exists()
