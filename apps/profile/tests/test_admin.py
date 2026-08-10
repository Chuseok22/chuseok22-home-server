import io

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from apps.profile.models import Profile, VisitorCounter


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_profile가_이미_있으면_admin_추가_화면이_차단된다(admin_client: Client) -> None:
    Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    response = admin_client.get(reverse('admin:profile_profile_add'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_visitorcounter가_이미_있으면_admin_추가_화면이_차단된다(admin_client: Client) -> None:
    VisitorCounter.objects.create(pk=1, count=0)

    response = admin_client.get(reverse('admin:profile_visitorcounter_add'))

    assert response.status_code == 403


def _make_avatar_upload(size: tuple[int, int] = (100, 50)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new('RGB', size, color='green').save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile('avatar.png', buffer.read(), content_type='image/png')


@pytest.mark.django_db
def test_아바타_업로드시_크롭_좌표대로_저장된다(admin_client: Client, settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload = _make_avatar_upload()

    response = admin_client.post(reverse('admin:profile_profile_add'), {
        'name': '백지훈',
        'tagline': '백엔드 개발자',
        'avatar': upload,
        'avatar_crop_x': 25,
        'avatar_crop_y': 0,
        'avatar_crop_width': 50,
        'avatar_crop_height': 50,
        'bio': '',
        'email': '',
        'github_url': '',
        'blog_url': '',
        'linkedin_url': '',
        'contribution_graph_url': '',
        '_save': 'Save',
    })

    assert response.status_code == 302
    profile = Profile.objects.get(name='백지훈')
    with Image.open(profile.avatar.path) as saved_image:
        assert saved_image.size == (50, 50)


@pytest.mark.django_db
def test_크롭_좌표_없이_아바타_업로드시_중앙_정사각형으로_저장된다(admin_client: Client, settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload = _make_avatar_upload()

    response = admin_client.post(reverse('admin:profile_profile_add'), {
        'name': '백지훈',
        'tagline': '백엔드 개발자',
        'avatar': upload,
        'bio': '',
        'email': '',
        'github_url': '',
        'blog_url': '',
        'linkedin_url': '',
        'contribution_graph_url': '',
        '_save': 'Save',
    })

    assert response.status_code == 302
    profile = Profile.objects.get(name='백지훈')
    with Image.open(profile.avatar.path) as saved_image:
        assert saved_image.size == (50, 50)  # 100x50 원본의 중앙 정사각형


@pytest.mark.django_db
def test_change_화면에서_아바타를_교체해도_크롭_좌표대로_저장된다(admin_client: Client, settings, tmp_path) -> None:
    # SingletonAdminMixin 때문에 Profile은 최초 1건만 add로 만들 수 있고, 실사용 시 아바타
    # 재업로드는 항상 change 화면에서 일어난다. add 화면 테스트만으로는 이 경로가 검증되지 않는다.
    settings.MEDIA_ROOT = tmp_path
    profile = Profile.objects.create(name='백지훈', tagline='백엔드 개발자')
    upload = _make_avatar_upload()

    response = admin_client.post(reverse('admin:profile_profile_change', args=[profile.pk]), {
        'name': '백지훈',
        'tagline': '백엔드 개발자',
        'avatar': upload,
        'avatar_crop_x': 25,
        'avatar_crop_y': 0,
        'avatar_crop_width': 50,
        'avatar_crop_height': 50,
        'bio': '',
        'email': '',
        'github_url': '',
        'blog_url': '',
        'linkedin_url': '',
        'contribution_graph_url': '',
        '_save': 'Save',
    })

    assert response.status_code == 302
    profile.refresh_from_db()
    with Image.open(profile.avatar.path) as saved_image:
        assert saved_image.size == (50, 50)


@pytest.mark.django_db
def test_activity_change_화면에_첨부파일_인라인이_보인다(admin_client: Client) -> None:
    from apps.profile.models import Activity

    activity = Activity.objects.create(name='인라인 테스트 활동', start_year=2026, order=0)

    response = admin_client.get(reverse('admin:profile_activity_change', args=[activity.pk]))

    assert response.status_code == 200
    assert 'name="attachments-0-file"' in response.content.decode()


@pytest.mark.django_db
def test_activity_change_화면에_링크_위젯_정적_자산이_포함된다(admin_client: Client) -> None:
    from apps.profile.models import Activity

    activity = Activity.objects.create(name='링크 위젯 테스트 활동', start_year=2026, order=0)

    response = admin_client.get(reverse('admin:profile_activity_change', args=[activity.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'id="id_links"' in content
    assert 'profile/admin/activity_links_widget.js' in content
    assert 'profile/admin/activity_links_widget.css' in content
