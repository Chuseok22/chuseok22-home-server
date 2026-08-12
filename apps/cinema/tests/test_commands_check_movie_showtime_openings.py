from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.cinema.management.commands.check_movie_showtime_openings import Command
from apps.cinema.models import NowShowingMovie, OpenedShowDate, TrackedMovie


@pytest.mark.django_db
def test_이미_알림_보낸_날짜가_없으면_오늘부터_버퍼일수만큼_확인한다() -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    command = Command()

    dates = command._build_candidate_dates([tracked])

    today = timezone.localdate()
    assert dates == [today, today + timedelta(days=1), today + timedelta(days=2)]


@pytest.mark.django_db
def test_이미_알림_보낸_날짜가_있으면_그_다음날부터_확인한다() -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    today = timezone.localdate()
    OpenedShowDate.objects.create(
        tracked_movie=tracked, show_date=today + timedelta(days=5), showtimes=[], notify_succeeded=True,
    )
    command = Command()

    dates = command._build_candidate_dates([tracked])

    assert dates == [today + timedelta(days=6), today + timedelta(days=7), today + timedelta(days=8)]


@pytest.mark.django_db
def test_발송_실패한_날짜는_프런티어_버퍼_밖이어도_후보에_남는다() -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    today = timezone.localdate()
    OpenedShowDate.objects.create(
        tracked_movie=tracked, show_date=today + timedelta(days=5), showtimes=[], notify_succeeded=False,
    )
    command = Command()

    dates = command._build_candidate_dates([tracked])

    assert dates == [today, today + timedelta(days=1), today + timedelta(days=2), today + timedelta(days=5)]


@pytest.mark.django_db
def test_발송_실패한_날짜는_더_늦은_날짜의_발송_성공으로_프런티어가_전진해도_후보에서_빠지지_않는다() -> None:
    """한 크롤에서 여러 날짜가 열려 앞쪽 날짜(실패)와 뒤쪽 날짜(성공)가 함께 발견된 경우,
    프런티어는 성공한 뒤쪽 날짜 기준으로 전진하지만 실패한 앞쪽 날짜는 계속 재시도돼야 한다."""
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    today = timezone.localdate()
    OpenedShowDate.objects.create(
        tracked_movie=tracked, show_date=today + timedelta(days=5), showtimes=[], notify_succeeded=False,
    )
    OpenedShowDate.objects.create(
        tracked_movie=tracked, show_date=today + timedelta(days=8), showtimes=[], notify_succeeded=True,
    )
    command = Command()

    dates = command._build_candidate_dates([tracked])

    assert today + timedelta(days=5) in dates
    assert dates == [
        today + timedelta(days=5), today + timedelta(days=9),
        today + timedelta(days=10), today + timedelta(days=11),
    ]


@pytest.mark.django_db
def test_14일_horizon을_넘는_날짜는_후보에서_제외된다() -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    today = timezone.localdate()
    OpenedShowDate.objects.create(
        tracked_movie=tracked, show_date=today + timedelta(days=13), showtimes=[], notify_succeeded=True,
    )
    command = Command()

    dates = command._build_candidate_dates([tracked])

    assert dates == [today + timedelta(days=14)]


@pytest.mark.django_db
def test_handle는_상영관별로_run_showtime_check을_호출한다() -> None:
    command = Command()
    with patch(
        'apps.cinema.management.commands.check_movie_showtime_openings.run_showtime_check',
        return_value=0,
    ) as mock_check:
        command.handle()

    assert mock_check.call_count == 2
    called_screens = {call.args[0] for call in mock_check.call_args_list}
    assert called_screens == {'cgv_yongsan_imax', 'lotte_jamsil_superplex'}


@pytest.mark.django_db
def test_handle는_상영_종료된_영화의_감시_대상을_후보_계산에서_제외한다() -> None:
    movie = NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='종료된영화', title='종료된영화',
        is_currently_showing=False,
    )
    TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    command = Command()
    with patch(
        'apps.cinema.management.commands.check_movie_showtime_openings.run_showtime_check',
        return_value=0,
    ) as mock_check:
        command.handle()

    cgv_call = next(call for call in mock_check.call_args_list if call.args[0] == 'cgv_yongsan_imax')
    assert cgv_call.args[2] == []
