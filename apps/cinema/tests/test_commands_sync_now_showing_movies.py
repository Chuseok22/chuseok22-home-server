from unittest.mock import MagicMock, patch

import pytest

from apps.cinema.crawlers.base import NowShowingMovieItem
from apps.cinema.management.commands.sync_now_showing_movies import Command
from apps.cinema.models import NowShowingMovie


@pytest.mark.django_db
def test_새로_보이는_영화는_생성되고_사라진_영화는_비활성화된다() -> None:
    NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='옛날영화', title='옛날영화', is_currently_showing=True,
    )
    mock_crawler = MagicMock()
    mock_crawler.list_now_showing.return_value = [
        NowShowingMovieItem(movie_code='새영화', title='새영화'),
    ]

    command = Command()
    with patch.object(command, '_crawlers', {'cgv_yongsan_imax': mock_crawler}):
        command.handle()

    old = NowShowingMovie.objects.get(cinema_screen='cgv_yongsan_imax', movie_code='옛날영화')
    new = NowShowingMovie.objects.get(cinema_screen='cgv_yongsan_imax', movie_code='새영화')
    assert old.is_currently_showing is False
    assert new.is_currently_showing is True


@pytest.mark.django_db
def test_크롤러가_빈_목록을_반환하면_기존_영화를_비활성화하지_않는다() -> None:
    NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='기존영화', title='기존영화', is_currently_showing=True,
    )
    mock_crawler = MagicMock()
    mock_crawler.list_now_showing.return_value = []

    command = Command()
    with patch.object(command, '_crawlers', {'cgv_yongsan_imax': mock_crawler}):
        command.handle()

    existing = NowShowingMovie.objects.get(cinema_screen='cgv_yongsan_imax', movie_code='기존영화')
    assert existing.is_currently_showing is True


@pytest.mark.django_db
def test_크롤링_실패해도_다른_상영관_동기화는_계속된다() -> None:
    failing_crawler = MagicMock()
    failing_crawler.list_now_showing.side_effect = Exception('boom')
    ok_crawler = MagicMock()
    ok_crawler.list_now_showing.return_value = [NowShowingMovieItem(movie_code='X', title='X')]

    command = Command()
    with patch.object(command, '_crawlers', {
        'cgv_yongsan_imax': failing_crawler, 'lotte_jamsil_superplex': ok_crawler,
    }):
        command.handle()

    assert NowShowingMovie.objects.filter(cinema_screen='lotte_jamsil_superplex', movie_code='X').exists()
