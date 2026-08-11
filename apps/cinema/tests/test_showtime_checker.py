from datetime import date
from unittest.mock import MagicMock

import pytest

from apps.cinema.crawlers.base import CinemaCrawlerError
from apps.cinema.models import CinemaScreenWatchStatus, NowShowingMovie, OpenedShowDate, TrackedMovie
from apps.cinema.services.showtime_checker import run_showtime_check

_SCREEN = 'cgv_yongsan_imax'
_LABEL = 'CGV 용산아이파크몰 IMAX'
_BOOKING_URL = 'https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013'


@pytest.fixture
def tracked_movie(db) -> TrackedMovie:
    movie = NowShowingMovie.objects.create(cinema_screen=_SCREEN, movie_code='영화A', title='영화A')
    return TrackedMovie.objects.create(
        cinema_screen=_SCREEN, movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )


@pytest.mark.django_db
def test_새로_열린_날짜가_있으면_OpenedShowDate를_만들고_알림을_보낸다(tracked_movie) -> None:
    crawler = MagicMock()
    crawler.get_open_dates_bulk.return_value = {'영화A': {date(2026, 9, 5): ['10:00', '15:00']}}
    discord = MagicMock()
    discord.send_new_date_alert.return_value = True

    notified_count = run_showtime_check(
        _SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord,
    )

    assert notified_count == 1
    opened = OpenedShowDate.objects.get(tracked_movie=tracked_movie, show_date=date(2026, 9, 5))
    assert opened.notify_succeeded is True
    discord.send_new_date_alert.assert_called_once_with(
        webhook_url='https://discord.com/api/webhooks/1/a',
        cinema_screen_label=_LABEL, movie_title='영화A', show_date=date(2026, 9, 5),
        showtimes=['10:00', '15:00'], booking_url=_BOOKING_URL,
    )


@pytest.mark.django_db
def test_이미_성공적으로_알린_날짜는_다시_알리지_않는다(tracked_movie) -> None:
    OpenedShowDate.objects.create(
        tracked_movie=tracked_movie, show_date=date(2026, 9, 5), showtimes=['10:00'],
        notify_succeeded=True,
    )
    crawler = MagicMock()
    crawler.get_open_dates_bulk.return_value = {'영화A': {date(2026, 9, 5): ['10:00']}}
    discord = MagicMock()

    notified_count = run_showtime_check(
        _SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord,
    )

    assert notified_count == 0
    discord.send_new_date_alert.assert_not_called()


@pytest.mark.django_db
def test_이전에_발송_실패한_날짜는_다음_주기에_재시도된다(tracked_movie) -> None:
    """Discord 발송이 실패해도 행은 이미 만들어져 있을 수 있다(get_or_create가 먼저 행을
    만든다) — notify_succeeded=False로 남아 있으면 다음 체크 주기에 재시도해야 알림이
    영구히 유실되지 않는다."""
    OpenedShowDate.objects.create(
        tracked_movie=tracked_movie, show_date=date(2026, 9, 5), showtimes=['10:00'],
        notify_succeeded=False,
    )
    crawler = MagicMock()
    crawler.get_open_dates_bulk.return_value = {'영화A': {date(2026, 9, 5): ['10:00']}}
    discord = MagicMock()
    discord.send_new_date_alert.return_value = True

    notified_count = run_showtime_check(
        _SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord,
    )

    assert notified_count == 1
    discord.send_new_date_alert.assert_called_once()
    opened = OpenedShowDate.objects.get(tracked_movie=tracked_movie, show_date=date(2026, 9, 5))
    assert opened.notify_succeeded is True


@pytest.mark.django_db
def test_발송_실패시_notify_succeeded는_False로_남아_재시도_대상이_된다(tracked_movie) -> None:
    crawler = MagicMock()
    crawler.get_open_dates_bulk.return_value = {'영화A': {date(2026, 9, 5): ['10:00']}}
    discord = MagicMock()
    discord.send_new_date_alert.return_value = False

    notified_count = run_showtime_check(
        _SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord,
    )

    assert notified_count == 0
    opened = OpenedShowDate.objects.get(tracked_movie=tracked_movie, show_date=date(2026, 9, 5))
    assert opened.notify_succeeded is False


@pytest.mark.django_db
def test_감시_대상이_없으면_크롤러를_호출하지_않는다() -> None:
    crawler = MagicMock()
    discord = MagicMock()

    notified_count = run_showtime_check(
        _SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord,
    )

    assert notified_count == 0
    crawler.get_open_dates_bulk.assert_not_called()


@pytest.mark.django_db
def test_candidate_dates가_비어있으면_크롤러를_호출하지_않고_실패_카운터도_건드리지_않는다(
    tracked_movie,
) -> None:
    CinemaScreenWatchStatus.objects.create(
        cinema_screen=_SCREEN, consecutive_failure_count=3, alert_sent=False,
    )
    crawler = MagicMock()
    discord = MagicMock()

    notified_count = run_showtime_check(_SCREEN, crawler, [], _LABEL, _BOOKING_URL, discord)

    assert notified_count == 0
    crawler.get_open_dates_bulk.assert_not_called()
    status = CinemaScreenWatchStatus.objects.get(cinema_screen=_SCREEN)
    assert status.consecutive_failure_count == 3


@pytest.mark.django_db
def test_예상치_못한_예외도_실패_카운터를_증가시킨다(tracked_movie) -> None:
    crawler = MagicMock()
    crawler.get_open_dates_bulk.side_effect = AttributeError('예상 못 한 크롤러 내부 오류')
    discord = MagicMock()

    run_showtime_check(_SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord)

    status = CinemaScreenWatchStatus.objects.get(cinema_screen=_SCREEN)
    assert status.consecutive_failure_count == 1


@pytest.mark.django_db
def test_상영_종료된_영화의_감시_대상은_제외된다() -> None:
    movie = NowShowingMovie.objects.create(
        cinema_screen=_SCREEN, movie_code='종료된영화', title='종료된영화', is_currently_showing=False,
    )
    TrackedMovie.objects.create(
        cinema_screen=_SCREEN, movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    crawler = MagicMock()
    discord = MagicMock()

    notified_count = run_showtime_check(
        _SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord,
    )

    assert notified_count == 0
    crawler.get_open_dates_bulk.assert_not_called()


@pytest.mark.django_db
def test_크롤링_실패시_연속_실패_카운터가_증가한다(tracked_movie) -> None:
    crawler = MagicMock()
    crawler.get_open_dates_bulk.side_effect = CinemaCrawlerError('실패')
    discord = MagicMock()

    run_showtime_check(_SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord)

    status = CinemaScreenWatchStatus.objects.get(cinema_screen=_SCREEN)
    assert status.consecutive_failure_count == 1
    assert status.alert_sent is False


@pytest.mark.django_db
def test_연속_5회_실패시_실패_알림을_1회_보낸다(tracked_movie) -> None:
    CinemaScreenWatchStatus.objects.create(cinema_screen=_SCREEN, consecutive_failure_count=4)
    crawler = MagicMock()
    crawler.get_open_dates_bulk.side_effect = CinemaCrawlerError('실패')
    discord = MagicMock()

    run_showtime_check(_SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord)

    status = CinemaScreenWatchStatus.objects.get(cinema_screen=_SCREEN)
    assert status.consecutive_failure_count == 5
    assert status.alert_sent is True
    discord.send_failure_alert.assert_called_once_with(
        ['https://discord.com/api/webhooks/1/a'], _LABEL,
    )


@pytest.mark.django_db
def test_5회_이상_실패해도_alert_sent가_True면_재발송하지_않는다(tracked_movie) -> None:
    CinemaScreenWatchStatus.objects.create(
        cinema_screen=_SCREEN, consecutive_failure_count=6, alert_sent=True,
    )
    crawler = MagicMock()
    crawler.get_open_dates_bulk.side_effect = CinemaCrawlerError('실패')
    discord = MagicMock()

    run_showtime_check(_SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord)

    discord.send_failure_alert.assert_not_called()


@pytest.mark.django_db
def test_성공하면_연속_실패_카운터가_리셋된다(tracked_movie) -> None:
    CinemaScreenWatchStatus.objects.create(
        cinema_screen=_SCREEN, consecutive_failure_count=3, alert_sent=False,
    )
    crawler = MagicMock()
    crawler.get_open_dates_bulk.return_value = {'영화A': {}}
    discord = MagicMock()

    run_showtime_check(_SCREEN, crawler, [date(2026, 9, 5)], _LABEL, _BOOKING_URL, discord)

    status = CinemaScreenWatchStatus.objects.get(cinema_screen=_SCREEN)
    assert status.consecutive_failure_count == 0
