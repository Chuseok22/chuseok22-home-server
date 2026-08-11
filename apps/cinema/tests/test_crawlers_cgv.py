from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.cinema.crawlers.base import CinemaCrawlerError
from apps.cinema.crawlers.cgv import CgvYongsanImaxCrawler

_SAMPLE_RESPONSE = {
    'data': [
        {
            'movNm': '스파이더맨: 브랜드 뉴 데이', 'scnsNm': '1관(IMAX)', 'movkndDsplNm': '2D',
            'scnsrtTm': '1030', 'scnendTm': '1250', 'frSeatCnt': 50, 'stcnt': 300,
            'scnsNo': '01', 'scnSseq': '1',
        },
        {
            'movNm': '스파이더맨: 브랜드 뉴 데이', 'scnsNm': '1관(IMAX)', 'movkndDsplNm': '2D',
            'scnsrtTm': '1500', 'scnendTm': '1720', 'frSeatCnt': 60, 'stcnt': 300,
            'scnsNo': '01', 'scnSseq': '2',
        },
        {
            'movNm': '어떤 2D 영화', 'scnsNm': '3관', 'movkndDsplNm': '2D',
            'scnsrtTm': '1100', 'scnendTm': '1300', 'frSeatCnt': 40, 'stcnt': 150,
            'scnsNo': '03', 'scnSseq': '1',
        },
    ],
}


@pytest.fixture
def crawler() -> CgvYongsanImaxCrawler:
    return CgvYongsanImaxCrawler()


class TestListNowShowing:
    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_IMAX_상영관만_추리고_중복_영화명은_제거한다(self, mock_get, crawler) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = _SAMPLE_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = crawler.list_now_showing(reference_date=date(2026, 9, 1))

        titles = [item.title for item in result]
        assert titles == ['스파이더맨: 브랜드 뉴 데이']

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_요청_실패시_CinemaCrawlerError를_발생시킨다(self, mock_get, crawler) -> None:
        mock_get.side_effect = requests.ConnectionError('boom')

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 9, 1))

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_data가_리스트가_아니면_CinemaCrawlerError를_발생시킨다(self, mock_get, crawler) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {'data': {'unexpected': 'shape'}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 9, 1))


class TestGetOpenDatesBulk:
    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_감시중인_영화의_IMAX_상영시간만_모아_반환한다(self, mock_get, crawler) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = _SAMPLE_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = crawler.get_open_dates_bulk(
            movie_codes=['스파이더맨: 브랜드 뉴 데이'],
            candidate_dates=[date(2026, 9, 1)],
        )

        assert result['스파이더맨: 브랜드 뉴 데이'][date(2026, 9, 1)] == ['10:30', '15:00']

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_감시중이지_않은_영화나_열리지_않은_날짜는_결과에_없다(self, mock_get, crawler) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {'data': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = crawler.get_open_dates_bulk(
            movie_codes=['아직_안_열린_영화'], candidate_dates=[date(2026, 9, 10)],
        )

        assert result['아직_안_열린_영화'] == {}
