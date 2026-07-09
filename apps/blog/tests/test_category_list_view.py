import pytest
from django.test import Client
from django.urls import reverse

from apps.blog.models import Category


@pytest.mark.django_db
def test_카테고리_목록을_반환한다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    parent = Category.objects.create(name='개발', slug='dev')
    Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    url = reverse('blog-category-list')

    response = client.get(url, HTTP_X_BLOG_INGEST_KEY='secret-key')

    assert response.status_code == 200
    body = response.json()
    assert {'name': '개발', 'slug': 'dev', 'parent_name': None} in body
    assert {'name': 'waitee-app', 'slug': 'waitee-app', 'parent_name': '개발'} in body


@pytest.mark.django_db
def test_키가_없으면_403이다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    url = reverse('blog-category-list')

    response = client.get(url)

    assert response.status_code == 403
