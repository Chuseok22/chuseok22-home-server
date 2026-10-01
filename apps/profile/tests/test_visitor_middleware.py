from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.profile.models import DailyVisitor
from apps.profile.services.visitor_counter import VISITED_COOKIE_NAME

BROWSER_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'


def _today_count() -> int:
    visitor = DailyVisitor.objects.filter(date=timezone.localdate()).first()
    return visitor.count if visitor else 0


@pytest.mark.django_db
def test_site_페이지_첫_방문은_집계되고_쿠키가_세팅된다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    response = client.get(reverse('site:home'))

    assert _today_count() == 1
    cookie = response.cookies[VISITED_COOKIE_NAME]
    assert cookie.value == timezone.localdate().isoformat()
    assert cookie['httponly']
    assert cookie['samesite'] == 'Lax'
    assert 1 <= int(cookie['max-age']) <= 86400


@pytest.mark.django_db
def test_쿠키가_세팅된_뒤_같은_날_재방문은_집계되지_않는다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    client.get(reverse('site:home'))
    client.get(reverse('site:home'))
    client.get(reverse('site:blog-list'))

    assert _today_count() == 1


@pytest.mark.django_db
def test_홈이_아니어도_site_페이지로_처음_들어오면_집계된다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    client.get(reverse('site:blog-list'))

    assert _today_count() == 1


@pytest.mark.django_db
def test_secure_속성은_SESSION_COOKIE_SECURE_설정을_따른다(settings) -> None:
    settings.SESSION_COOKIE_SECURE = True
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    response = client.get(reverse('site:home'))

    assert response.cookies[VISITED_COOKIE_NAME]['secure']


@pytest.mark.django_db
def test_어제_날짜_쿠키가_남아있으면_새_날로_다시_집계된다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)
    yesterday = timezone.localdate() - timedelta(days=1)
    client.cookies[VISITED_COOKIE_NAME] = yesterday.isoformat()

    response = client.get(reverse('site:home'))

    assert _today_count() == 1
    assert response.cookies[VISITED_COOKIE_NAME].value == timezone.localdate().isoformat()


@pytest.mark.django_db
def test_위조된_쿠키_값이면_예외없이_집계되고_정상_쿠키로_교체된다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)
    client.cookies[VISITED_COOKIE_NAME] = 'not-a-date'

    response = client.get(reverse('site:home'))

    assert response.status_code == 200
    assert _today_count() == 1
    assert response.cookies[VISITED_COOKIE_NAME].value == timezone.localdate().isoformat()


@pytest.mark.django_db
def test_봇_User_Agent는_집계되지_않고_쿠키도_세팅되지_않는다() -> None:
    client = Client(HTTP_USER_AGENT='Googlebot/2.1 (+http://www.google.com/bot.html)')

    response = client.get(reverse('site:home'))

    assert _today_count() == 0
    assert VISITED_COOKIE_NAME not in response.cookies


@pytest.mark.django_db
def test_관리자_방문은_집계되지_않는다() -> None:
    staff_user = User.objects.create_user(username='staff', password='pw12345!', is_staff=True)
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)
    client.force_login(staff_user)

    client.get(reverse('site:home'))

    assert _today_count() == 0


@pytest.mark.django_db
def test_로그인한_일반_사용자는_집계된다() -> None:
    member = User.objects.create_user(username='member', password='pw12345!')
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)
    client.force_login(member)

    client.get(reverse('site:home'))

    assert _today_count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize('method', ['head', 'post'])
def test_GET이_아닌_요청은_집계되지_않는다(method: str) -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    getattr(client, method)(reverse('site:home'))

    assert _today_count() == 0


@pytest.mark.django_db
def test_site_네임스페이스가_아닌_경로는_집계되지_않는다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    client.get(reverse('admin:login'))

    assert _today_count() == 0


@pytest.mark.django_db
def test_집계_중_DB_오류가_나도_페이지는_200이고_쿠키와_행이_남지_않는다(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_database_error(visit_date: date) -> None:
        raise DatabaseError('집계 실패')

    monkeypatch.setattr('apps.profile.middleware.record_visit', raise_database_error)
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    response = client.get(reverse('site:home'))

    assert response.status_code == 200
    assert VISITED_COOKIE_NAME not in response.cookies
    assert not DailyVisitor.objects.exists()


@pytest.mark.django_db
def test_존재하지_않는_경로_404는_집계되지_않는다() -> None:
    client = Client(HTTP_USER_AGENT=BROWSER_USER_AGENT)

    response = client.get('/wp-login.php')

    assert response.status_code == 404
    assert _today_count() == 0
    assert VISITED_COOKIE_NAME not in response.cookies
