import io

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from apps.blog.models import Category, Post


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def category(db) -> Category:
    return Category.objects.create(name='개발', slug='dev')


@pytest.mark.django_db
def test_태그가_빈값이어도_저장된다(admin_client: Client, category: Category) -> None:
    url = reverse('admin:blog_post_add')
    response = admin_client.post(url, {
        'title': '테스트 포스트',
        'slug': 'test-post',
        'summary': '',
        'category': category.id,
        'repo_url': '',
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
    assert '<h1>헤딩</h1>' in response.content.decode()


def _make_png_upload(name: str) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new('RGB', (5, 5), color='green').save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')


@pytest.mark.django_db
def test_로그인하지_않으면_업로드_엔드포인트_접근이_거부된다() -> None:
    client = Client()
    url = reverse('admin:blog_post_upload_media')
    upload = _make_png_upload('photo.png')

    response = client.post(url, {'file': upload})

    assert response.status_code == 302  # admin_site.admin_view()가 미인증 요청을 로그인 페이지로 redirect


@pytest.mark.django_db
def test_post_변경_권한이_없는_스태프는_업로드가_거부된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(username='staff', email='staff@example.com', password='pw12345!', is_staff=True)
    client = Client()
    client.force_login(user)
    url = reverse('admin:blog_post_upload_media')
    upload = _make_png_upload('photo.png')

    response = client.post(url, {'file': upload})

    assert response.status_code == 403


@pytest.mark.django_db
def test_관리자는_이미지를_업로드하고_마크다운을_응답받는다(admin_client: Client, settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    url = reverse('admin:blog_post_upload_media')
    upload = _make_png_upload('photo.png')

    response = admin_client.post(url, {'file': upload})

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['url'].endswith('.webp')
    assert '![업로드 이미지]' in data['markdown']


@pytest.mark.django_db
def test_카테고리_admin에서_소분류는_상위_카테고리_선택지에_없다(admin_client: Client) -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)

    url = reverse('admin:blog_category_add')
    response = admin_client.get(url)

    parent_choices = list(response.context['adminform'].form.fields['parent'].queryset)
    assert child not in parent_choices
    assert parent in parent_choices


@pytest.mark.django_db
def test_카테고리_admin_수정화면에서_자기_자신은_상위_카테고리_선택지에_없다(admin_client: Client) -> None:
    parent = Category.objects.create(name='개발', slug='dev')
    other = Category.objects.create(name='일상', slug='daily')

    url = reverse('admin:blog_category_change', args=[parent.pk])
    response = admin_client.get(url)

    parent_choices = list(response.context['adminform'].form.fields['parent'].queryset)
    assert parent not in parent_choices
    assert other in parent_choices


@pytest.mark.django_db
def test_슬러그를_비워두면_Post가_자동_생성한다(admin_client: Client, category: Category) -> None:
    url = reverse('admin:blog_post_add')
    response = admin_client.post(url, {
        'title': '슬러그 자동생성 테스트',
        'slug': '',
        'summary': '',
        'category': category.id,
        'repo_url': '',
        'content': '# 제목',
        'tags': '',
        'is_published': '',
        'published_at_0': '',
        'published_at_1': '',
        '_save': 'Save',
    })

    assert response.status_code == 302
    post = Post.objects.get(title='슬러그 자동생성 테스트')
    assert post.slug != ''


@pytest.mark.django_db
def test_슬러그를_비워두면_Category가_자동_생성한다(admin_client: Client) -> None:
    url = reverse('admin:blog_category_add')
    response = admin_client.post(url, {
        'name': '테스트카테고리',
        'slug': '',
    })

    assert response.status_code == 302
    category = Category.objects.get(name='테스트카테고리')
    assert category.slug != ''
