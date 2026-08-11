from datetime import date

import pytest

from apps.cinema.crawlers.base import BaseCinemaCrawler, NowShowingMovieItem


def test_BaseCinemaCrawler는_직접_인스턴스화할_수_없다() -> None:
    with pytest.raises(TypeError):
        BaseCinemaCrawler()


def test_NowShowingMovieItem은_movie_code와_title을_가진다() -> None:
    item = NowShowingMovieItem(movie_code='24329', title='스파이더맨')
    assert item.movie_code == '24329'
    assert item.title == '스파이더맨'


def test_구체_구현체는_두_추상_메서드를_모두_구현해야_한다() -> None:
    class IncompleteCrawler(BaseCinemaCrawler):
        def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
            return []

    with pytest.raises(TypeError):
        IncompleteCrawler()
