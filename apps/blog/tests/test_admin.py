import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.blog.models import Post


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_태그가_빈값이어도_저장된다(admin_client: Client) -> None:
    url = reverse('admin:blog_post_add')
    response = admin_client.post(url, {
        'title': '테스트 포스트',
        'slug': 'test-post',
        'summary': '',
        'content': '# 제목',
        'tags': '',
        'is_published': '',
        'published_at_0': '',
        'published_at_1': '',
        '_save': 'Save',
    })

    assert response.status_code == 302
    post = Post.objects.get(slug='test-post')
    assert post.tags == []


@pytest.mark.django_db
def test_마크다운_미리보기가_렌더링된다(admin_client: Client) -> None:
    post = Post.objects.create(title='제목', slug='preview-post', content='# 헤딩')
    url = reverse('admin:blog_post_change', args=[post.pk])

    response = admin_client.get(url)

    assert response.status_code == 200
    assert b'<h1>' in response.content
