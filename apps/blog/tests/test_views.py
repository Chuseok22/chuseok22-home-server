import pytest
from django.test import Client
from django.urls import reverse

from apps.blog.models import Category, Post


@pytest.mark.django_db
def test_올바른_키로_요청하면_초안이_생성된다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={
            'title': '작업 회고',
            'content': '# 배경\n...',
            'category_name': 'waitee-app',
        },
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 201
    post = Post.objects.get(id=response.json()['id'])
    assert post.is_published is False
    assert post.category.name == 'waitee-app'
    assert post.category.parent.name == '개발'


@pytest.mark.django_db
def test_키가_틀리면_403이다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={'title': '작업 회고', 'content': '내용', 'category_name': 'waitee-app'},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='wrong-key',
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_필수_필드가_없으면_400이다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={'content': '내용'},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_같은_저장소로_두번_요청해도_카테고리는_하나만_생성된다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    url = reverse('blog-ingest')
    payload = {'title': '작업 회고', 'content': '내용', 'category_name': 'waitee-app'}

    client.post(url, data=payload, content_type='application/json', HTTP_X_BLOG_INGEST_KEY='secret-key')
    client.post(url, data={**payload, 'title': '두번째 회고'}, content_type='application/json', HTTP_X_BLOG_INGEST_KEY='secret-key')

    assert Category.objects.filter(name='waitee-app').count() == 1
