import pytest
from django.test import Client
from django.urls import reverse

from apps.blog.models import Category, Post, Tag


@pytest.mark.django_db
def test_올바른_키로_요청하면_초안이_생성된다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    parent = Category.objects.create(name='개발', slug='dev')
    Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
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
def test_존재하지_않는_카테고리면_422이다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={'title': '작업 회고', 'content': '내용', 'category_name': '없는-카테고리'},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 422
    assert '없는-카테고리' in response.json()['detail']


@pytest.mark.django_db
def test_대분류_이름으로도_등록된다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    Category.objects.create(name='일상', slug='daily')
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={'title': '오늘의 기록', 'content': '내용', 'category_name': '일상'},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 201
    post = Post.objects.get(id=response.json()['id'])
    assert post.category.name == '일상'
    assert post.category.parent is None


@pytest.mark.django_db
def test_is_published_true면_바로_공개되고_published_at이_설정된다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    Category.objects.create(name='일상', slug='daily')
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={
            'title': '공개 테스트',
            'content': '내용',
            'category_name': '일상',
            'is_published': True,
        },
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 201
    post = Post.objects.get(id=response.json()['id'])
    assert post.is_published is True
    assert post.published_at is not None


@pytest.mark.django_db
def test_is_published을_생략하면_초안으로_저장된다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    Category.objects.create(name='일상', slug='daily')
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={'title': '초안 테스트', 'content': '내용', 'category_name': '일상'},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 201
    post = Post.objects.get(id=response.json()['id'])
    assert post.is_published is False
    assert post.published_at is None


@pytest.mark.django_db
def test_ingest는_태그_목록을_Tag로_변환해서_연결한다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    Category.objects.create(name='일상', slug='daily')
    url = reverse('blog-ingest')

    response = client.post(
        url,
        data={'title': '태그 테스트', 'content': '내용', 'category_name': '일상', 'tags': ['Django', 'React']},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert response.status_code == 201
    post = Post.objects.get(id=response.json()['id'])
    assert {tag.name for tag in post.tags.all()} == {'Django', 'React'}


@pytest.mark.django_db
def test_ingest는_대소문자만_다른_태그를_기존_태그로_재사용한다(client: Client, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    Category.objects.create(name='일상', slug='daily')
    url = reverse('blog-ingest')

    client.post(
        url,
        data={'title': '첫 글', 'content': '내용', 'category_name': '일상', 'tags': ['Django']},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )
    client.post(
        url,
        data={'title': '둘째 글', 'content': '내용', 'category_name': '일상', 'tags': ['django']},
        content_type='application/json',
        HTTP_X_BLOG_INGEST_KEY='secret-key',
    )

    assert Tag.objects.count() == 1
