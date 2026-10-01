from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from apps.profile.models import DailyVisitor
from apps.profile.services.visitor_counter import (
    VisitCounts,
    get_visit_counts,
    is_bot_user_agent,
    record_visit,
    seconds_until_next_midnight,
    should_count_visit,
)

TODAY = date(2026, 10, 1)
BROWSER_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'


def _should_count(method: str = 'GET', visited_cookie_value: str | None = None, is_staff: bool = False,
                  user_agent: str = BROWSER_USER_AGENT) -> bool:
    return should_count_visit(
        method=method,
        visited_cookie_value=visited_cookie_value,
        is_staff=is_staff,
        user_agent=user_agent,
        today=TODAY,
    )


@pytest.mark.parametrize('user_agent', [
    'Googlebot/2.1 (+http://www.google.com/bot.html)',
    'GOOGLEBOT',
    'Mozilla/5.0 (compatible; bingbot/2.0)',
    'curl/8.4.0',
    'python-requests/2.32.0',
    'Slackbot-LinkExpanding 1.0',
    'Mozilla/5.0 (X11; Linux x86_64) HeadlessChrome/120.0',
    'Mozilla/5.0 (compatible; ExampleCrawler/1.0)',
    'Mozilla/5.0 (compatible; ExampleSpider/1.0)',
    'Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)',
    'LinkPreview/1.0',
    'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
    'Wget/1.21.4',
    'python-httpx/0.27.0',
])
def test_is_bot_user_agent는_봇_키워드를_대소문자_구분없이_판별한다(user_agent: str) -> None:
    assert is_bot_user_agent(user_agent) is True


@pytest.mark.parametrize('user_agent', [BROWSER_USER_AGENT, ''])
def test_is_bot_user_agent는_일반_브라우저와_빈_값을_봇으로_보지_않는다(user_agent: str) -> None:
    assert is_bot_user_agent(user_agent) is False


def test_should_count_visit은_쿠키가_없는_일반_GET이면_True다() -> None:
    assert _should_count() is True


def test_should_count_visit은_오늘_날짜_쿠키가_있으면_False다() -> None:
    assert _should_count(visited_cookie_value='2026-10-01') is False


def test_should_count_visit은_어제_날짜_쿠키면_True다() -> None:
    assert _should_count(visited_cookie_value='2026-09-30') is True


def test_should_count_visit은_위조된_쿠키_값이면_True다() -> None:
    assert _should_count(visited_cookie_value='<script>1</script>') is True


@pytest.mark.parametrize('method', ['POST', 'HEAD', 'PUT'])
def test_should_count_visit은_GET이_아니면_False다(method: str) -> None:
    assert _should_count(method=method) is False


def test_should_count_visit은_봇이면_False다() -> None:
    assert _should_count(user_agent='Googlebot/2.1') is False


def test_should_count_visit은_관리자면_False다() -> None:
    assert _should_count(is_staff=True) is False


@pytest.mark.django_db
def test_record_visit은_첫_호출에_행을_만들고_호출마다_1씩_증가시킨다() -> None:
    record_visit(TODAY)
    record_visit(TODAY)
    record_visit(TODAY)

    assert DailyVisitor.objects.count() == 1
    assert DailyVisitor.objects.get(date=TODAY).count == 3


@pytest.mark.django_db
def test_get_visit_counts는_기록이_없으면_0과_0을_반환한다() -> None:
    assert get_visit_counts(TODAY) == VisitCounts(today=0, total=0)


@pytest.mark.django_db
def test_get_visit_counts는_오늘은_오늘_행만_총합은_전체_행의_합을_반환한다() -> None:
    DailyVisitor.objects.create(date=date(2026, 9, 29), count=5)
    DailyVisitor.objects.create(date=date(2026, 9, 30), count=7)
    DailyVisitor.objects.create(date=TODAY, count=2)

    assert get_visit_counts(TODAY) == VisitCounts(today=2, total=14)


@pytest.mark.django_db
def test_get_visit_counts는_오늘_행이_없으면_today가_0이고_총합은_유지된다() -> None:
    DailyVisitor.objects.create(date=date(2026, 9, 30), count=7)

    assert get_visit_counts(TODAY) == VisitCounts(today=0, total=7)


def test_seconds_until_next_midnight은_다음_KST_자정까지_남은_초를_반환한다() -> None:
    seoul = ZoneInfo('Asia/Seoul')

    assert seconds_until_next_midnight(datetime(2026, 10, 1, 23, 0, 0, tzinfo=seoul)) == 3600
    assert seconds_until_next_midnight(datetime(2026, 10, 1, 12, 0, 0, tzinfo=seoul)) == 43200
    assert seconds_until_next_midnight(datetime(2026, 10, 1, 0, 0, 0, tzinfo=seoul)) == 86400


def test_seconds_until_next_midnight은_KST가_아닌_aware_입력도_KST로_변환해_계산한다() -> None:
    utc_afternoon = datetime(2026, 10, 1, 14, 0, tzinfo=ZoneInfo('UTC'))

    assert seconds_until_next_midnight(utc_afternoon) == 3600


def test_seconds_until_next_midnight은_자정_직전에도_1_이상이다() -> None:
    seoul = ZoneInfo('Asia/Seoul')

    assert seconds_until_next_midnight(datetime(2026, 10, 1, 23, 59, 59, 900000, tzinfo=seoul)) == 1
