from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from PIL import Image
from pytest_django.fixtures import SettingsWrapper

from apps.site.admin import ConnectProfileAdmin, ConnectProfileAdminForm
from apps.site.models import ConnectLink, ConnectProfile


def _build_link(**overrides: object) -> ConnectLink:
    values = {'title': 'GitHub', 'url': 'https://github.com/example'}
    values.update(overrides)
    return ConnectLink(**values)


@pytest.mark.django_db
def test_connect_link는_order_오름차순으로_정렬된다() -> None:
    ConnectLink.objects.create(title='둘째', url='https://example.com/2', order=2)
    ConnectLink.objects.create(title='첫째', url='https://example.com/0', order=0)
    ConnectLink.objects.create(title='중간', url='https://example.com/1', order=1)

    assert list(ConnectLink.objects.values_list('title', flat=True)) == ['첫째', '중간', '둘째']


def test_connect_link_icon_style은_정의되지_않은_값이면_검증에_실패한다() -> None:
    with pytest.raises(ValidationError):
        _build_link(icon_style='red').full_clean()

    _build_link(icon_style='instagram').full_clean()


@pytest.mark.parametrize(
    ('english_name', 'expected'),
    [('Jihoon Baek', 'JB'), ('jihoon', 'J'), ('  Jihoon  Min  Baek ', 'JB'), ('', '')],
)
def test_connect_profile_initials는_첫_단어와_마지막_단어의_첫_글자를_대문자로_반환한다(
    english_name: str, expected: str
) -> None:
    assert ConnectProfile(english_name=english_name).initials == expected


def test_connect_profile_title_lines는_crlf와_빈_줄을_정리한다() -> None:
    profile = ConnectProfile(title='A\r\n\r\n B \nC')

    assert profile.title_lines == ['A', 'B', 'C']


def test_connect_profile_phone은_허용되지_않는_문자를_거부한다() -> None:
    def build(phone: str) -> ConnectProfile:
        return ConnectProfile(english_name='Jihoon Baek', title='Student', phone=phone)

    build('+82-10-0000-0000').full_clean(exclude=['avatar'])

    for invalid_phone in ('010\r\nTEL:1', 'abc'):
        with pytest.raises(ValidationError):
            build(invalid_phone).full_clean(exclude=['avatar'])


@pytest.mark.django_db
def test_connect_profile_admin은_레코드가_있으면_추가_권한을_막는다() -> None:
    superuser = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'password')
    request = RequestFactory().get('/admin/')
    request.user = superuser
    model_admin = ConnectProfileAdmin(ConnectProfile, AdminSite())

    assert model_admin.has_add_permission(request) is True

    ConnectProfile.objects.create(english_name='Jihoon Baek', title='Student')

    assert model_admin.has_add_permission(request) is False


@pytest.mark.django_db
def test_connect_profile_admin_form은_새_아바타를_정사각형으로_크롭해_저장한다(
    settings: SettingsWrapper, tmp_path: Path
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image_buffer = BytesIO()
    Image.new('RGB', (200, 100), 'red').save(image_buffer, format='PNG')
    upload = SimpleUploadedFile('avatar.png', image_buffer.getvalue(), content_type='image/png')

    form = ConnectProfileAdminForm(
        data={'english_name': 'Jihoon Baek', 'title': 'Student', 'email': '', 'phone': ''},
        files={'avatar': upload},
    )

    assert form.is_valid(), form.errors
    profile = form.save()

    with Image.open(profile.avatar.path) as saved_image:
        assert saved_image.size == (100, 100)
