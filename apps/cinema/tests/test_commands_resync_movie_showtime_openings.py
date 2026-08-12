from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.cinema.management.commands.resync_movie_showtime_openings import Command, _MAX_HORIZON_DAYS


def test_후보_날짜는_오늘부터_MAX_HORIZON_DAYS까지_전체다() -> None:
    command = Command()

    dates = command._build_candidate_dates()

    today = timezone.localdate()
    assert dates == [today + timedelta(days=offset) for offset in range(_MAX_HORIZON_DAYS + 1)]


@pytest.mark.django_db
def test_handle는_상영관별로_run_showtime_check을_호출한다() -> None:
    command = Command()
    with patch(
        'apps.cinema.management.commands.resync_movie_showtime_openings.run_showtime_check',
        return_value=0,
    ) as mock_check:
        command.handle()

    assert mock_check.call_count == 2
    for call in mock_check.call_args_list:
        assert len(call.args[2]) == _MAX_HORIZON_DAYS + 1
        # run_showtime_check(cinema_screen, crawler, candidate_dates, cinema_screen_label, discord)
        # — booking_url이 빠진 5-인자 시그니처로 호출되는지 검증한다.
        assert len(call.args) == 5
