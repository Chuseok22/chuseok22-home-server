from pathlib import Path

import pytest
from django.db.models import Sum
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper

from apps.profile.models import DailyVisitor
from apps.site.models import ConnectLink, ConnectProfile

_USER_AGENT = 'Mozilla/5.0'


def _create_profile(**overrides: str) -> ConnectProfile:
    values = {
        'english_name': 'Jihoon Baek',
        'title': 'Computer Science and Engineering\nUndergraduate Student',
        'email': 'me@example.com',
        'phone': '+82-10-0000-0000',
    }
    values.update(overrides)
    return ConnectProfile.objects.create(**values)


def _get(client: Client, url_name: str, **extra: str) -> HttpResponse:
    return client.get(reverse(url_name), HTTP_USER_AGENT=_USER_AGENT, **extra)


@pytest.mark.django_db
def test_connect는_프로필이_없으면_404를_반환한다(client: Client) -> None:
    assert _get(client, 'site:connect').status_code == 404


@pytest.mark.django_db
def test_connect_vcard는_프로필이_없으면_404를_반환한다(client: Client) -> None:
    assert _get(client, 'site:connect-vcard').status_code == 404


@pytest.mark.django_db
def test_connect는_활성_링크만_order_순서로_렌더링한다(client: Client) -> None:
    _create_profile()
    ConnectLink.objects.create(title='Link-Bravo', url='https://example.com/b', order=1)
    ConnectLink.objects.create(title='Link-Alpha', url='https://example.com/a', order=0)
    ConnectLink.objects.create(title='Link-Hidden', url='https://example.com/h', order=2, is_active=False)

    content = _get(client, 'site:connect').content.decode()

    assert content.index('Link-Alpha') < content.index('Link-Bravo')
    assert 'Link-Hidden' not in content


@pytest.mark.django_db
def test_connect는_링크가_없어도_200이고_목록을_그리지_않는다(client: Client) -> None:
    _create_profile()

    response = _get(client, 'site:connect')

    assert response.status_code == 200
    assert 'a-list' not in response.content.decode()


@pytest.mark.django_db
def test_connect는_내비게이션과_챗봇_위젯을_렌더링하지_않는다(client: Client) -> None:
    _create_profile()

    content = _get(client, 'site:connect').content.decode()

    assert 'chatbot' not in content
    assert '<nav' not in content


@pytest.mark.django_db
def test_connect는_이름과_직함을_html_이스케이프한다(client: Client) -> None:
    _create_profile(title='<b>x</b>')

    content = _get(client, 'site:connect').content.decode()

    assert '&lt;b&gt;x&lt;/b&gt;' in content
    assert '<b>x</b>' not in content


@pytest.mark.django_db
def test_connect는_이름과_링크_텍스트도_html_이스케이프한다(client: Client) -> None:
    _create_profile(english_name='<i>n</i>')
    ConnectLink.objects.create(title='<script>x</script>', subtitle='"><b>', url='https://example.com/')

    content = _get(client, 'site:connect').content.decode()

    for raw_markup in ('<i>n</i>', '<script>x</script>', '"><b>'):
        assert raw_markup not in content
    assert '&lt;script&gt;x&lt;/script&gt;' in content


@pytest.mark.django_db
def test_connect는_아이콘이_없으면_img를_그리지_않고_전체_url_아이콘은_그대로_쓴다(client: Client) -> None:
    _create_profile()
    ConnectLink.objects.create(title='NoIcon', url='https://example.com/a', order=0)
    ConnectLink.objects.create(
        title='UrlIcon', url='https://example.com/b', icon='https://cdn.example.com/icon.svg', order=1
    )

    content = _get(client, 'site:connect').content.decode()

    assert content.count('<img') == 1
    assert 'src="https://cdn.example.com/icon.svg"' in content


@pytest.mark.django_db
def test_connect는_아바타가_있으면_img로_렌더링한다(client: Client, settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    profile = _create_profile()
    profile.avatar.save('face.png', SimpleUploadedFile('face.png', b'x'), save=True)

    content = _get(client, 'site:connect').content.decode()

    assert '<img class="a-avatar"' in content
    assert 'aria-hidden="true">JB</div>' not in content


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', ['site:connect', 'site:connect-vcard'])
def test_connect_뷰는_post_요청을_405로_거부한다(client: Client, url_name: str) -> None:
    _create_profile()

    assert client.post(reverse(url_name)).status_code == 405


@pytest.mark.django_db
def test_connect는_여러_줄_직함을_줄바꿈으로_렌더링한다(client: Client) -> None:
    _create_profile(title='Line1\r\nLine2')

    assert 'Line1<br>Line2' in _get(client, 'site:connect').content.decode()


@pytest.mark.django_db
def test_connect는_아바타가_없으면_이니셜을_표시한다(client: Client) -> None:
    _create_profile()

    assert 'aria-hidden="true">JB</div>' in _get(client, 'site:connect').content.decode()


@pytest.mark.django_db
def test_connect는_외부_링크에_noopener를_붙이고_icon_style_클래스를_쓴다(client: Client) -> None:
    _create_profile()
    ConnectLink.objects.create(
        title='Instagram',
        url='https://instagram.com/example',
        icon='instagram',
        icon_style=ConnectLink.IconStyle.INSTAGRAM,
    )

    content = _get(client, 'site:connect').content.decode()

    assert 'rel="noopener noreferrer"' in content
    assert 'a-ic-instagram' in content
    assert 'https://cdn.simpleicons.org/instagram' in content


@pytest.mark.django_db
def test_connect는_og_메타태그를_포함한다(client: Client) -> None:
    _create_profile()

    assert 'property="og:title"' in _get(client, 'site:connect').content.decode()


@pytest.mark.django_db
def test_connect_짧은_주소_c는_connect로_리다이렉트한다(client: Client) -> None:
    response = client.get('/c/')

    assert response.status_code == 302
    assert response['Location'] == reverse('site:connect')


@pytest.mark.django_db
def test_connect_vcard는_vcf_첨부_응답을_반환한다(client: Client) -> None:
    _create_profile()

    response = _get(client, 'site:connect-vcard')

    assert response['Content-Type'].startswith('text/vcard')
    assert response['Content-Disposition'] == 'attachment; filename="jihoon-baek.vcf"'
    assert response['X-Robots-Tag'] == 'noindex'
    body = response.content.decode()
    assert body.startswith('BEGIN:VCARD')
    assert 'URL:http://testserver/' in body


@pytest.mark.django_db
def test_connect_vcard는_비ascii_이름이면_contact_vcf_파일명을_쓴다(client: Client) -> None:
    _create_profile(english_name='백지훈')

    response = _get(client, 'site:connect-vcard')

    assert response['Content-Disposition'] == 'attachment; filename="contact.vcf"'


@pytest.mark.django_db
def test_connect_요청은_하루_한_번만_방문자로_집계된다(client: Client) -> None:
    _create_profile()

    client.get('/c/', HTTP_USER_AGENT=_USER_AGENT, follow=True)
    _get(client, 'site:connect')

    assert DailyVisitor.objects.aggregate(total=Sum('count'))['total'] == 1
