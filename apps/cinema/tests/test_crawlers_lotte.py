import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.cinema.crawlers.base import CinemaCrawlerError
from apps.cinema.crawlers.lotte import LotteJamsilSuperplexCrawler

_TICKETING_PAGE_RESPONSE = {
    'Movies': {'Movies': {'Items': [
        {'RepresentationMovieCode': 24329, 'MovieNameKR': '스파이더맨: 브랜드 뉴 데이'},
        {'RepresentationMovieCode': 24500, 'MovieNameKR': '수퍼플렉스에서_상영_안하는_영화'},
    ]}},
}


def _play_sequence_response(has_superplex: bool) -> dict:
    if not has_superplex:
        return {'PlaySeqs': {'Items': []}, 'IsOK': True}
    return {
        'PlaySeqs': {'Items': [
            {
                'ScreenDivisionNameKR': '수퍼플렉스', 'ScreenDivisionCode': 940,
                'ScreenID': 101621, 'ScreenNameKR': '21관',
                'PlayDt': '2026-08-11', 'PlaySequence': 1,
                'StartTime': '08:00', 'EndTime': '10:35',
                'TotalSeatCount': 295, 'BookingSeatCount': 203,
                'RepresentationMovieCode': '24329', 'MovieCode': '24634',
            },
            {
                'ScreenDivisionNameKR': '일반관', 'ScreenDivisionCode': 100,
                'ScreenID': 101600, 'ScreenNameKR': '5관',
                'PlayDt': '2026-08-11', 'PlaySequence': 1,
                'StartTime': '09:00', 'EndTime': '11:35',
                'TotalSeatCount': 150, 'BookingSeatCount': 40,
                'RepresentationMovieCode': '24329', 'MovieCode': '24634',
            },
        ]},
        'IsOK': True,
    }


@pytest.fixture
def crawler() -> LotteJamsilSuperplexCrawler:
    return LotteJamsilSuperplexCrawler()


class TestCall:
    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_실제_브라우저_요청에_포함되는_공통_파라미터와_Referer를_함께_보낸다(self, mock_post, crawler) -> None:
        """HAR 캡처로 확인된 실제 요청은 MethodName 외에 channelType/osType/osVersion/
        memberOnNo를 항상 포함하고 Referer 헤더를 보낸다 — 최대한 실제 트래픽에 맞춘다."""
        mock_post.return_value = MagicMock(raise_for_status=lambda: None, json=lambda: {'IsOK': 'true'})

        crawler._call('GetPlaySequence', {'playDate': '2026-08-11'})

        payload = json.loads(mock_post.call_args.kwargs['files']['paramList'][1])
        assert payload['channelType'] == 'HO'
        assert payload['osType'] == 'W'
        assert payload['memberOnNo'] == '0'
        assert 'osVersion' in payload
        assert mock_post.call_args.kwargs['headers']['Referer'] == 'https://www.lottecinema.co.kr/NLCHS/Ticketing'


class TestListNowShowing:
    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_수퍼플렉스에_회차가_있는_영화만_반환한다(self, mock_post, crawler) -> None:
        def _side_effect(*args, **kwargs) -> MagicMock:
            payload = kwargs['files']['paramList'][1]
            response = MagicMock()
            response.raise_for_status.return_value = None
            if 'GetTicketingPageTOBE' in payload:
                response.json.return_value = _TICKETING_PAGE_RESPONSE
            elif '24329' in payload:
                response.json.return_value = _play_sequence_response(has_superplex=True)
            else:
                response.json.return_value = _play_sequence_response(has_superplex=False)
            return response

        mock_post.side_effect = _side_effect

        result = crawler.list_now_showing(reference_date=date(2026, 8, 11))

        assert [item.movie_code for item in result] == ['24329']
        assert result[0].title == '스파이더맨: 브랜드 뉴 데이'

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_요청_실패시_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        mock_post.side_effect = requests.ConnectionError('boom')

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 8, 11))

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_응답이_dict가_아니면_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = ['unexpected', 'shape']
        mock_post.return_value = response

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 8, 11))


class TestGetOpenDatesBulk:
    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_수퍼플렉스_상영시간만_모아_반환한다(self, mock_post, crawler) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _play_sequence_response(has_superplex=True)
        mock_post.return_value = response

        result = crawler.get_open_dates_bulk(
            movie_codes=['24329'], candidate_dates=[date(2026, 8, 11)],
        )

        assert result['24329'][date(2026, 8, 11)] == ['08:00']

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_IsOK가_False면_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'IsOK': False, 'ErrorMessage': '일시적인 오류'}
        mock_post.return_value = response

        with pytest.raises(CinemaCrawlerError):
            crawler.get_open_dates_bulk(movie_codes=['24329'], candidate_dates=[date(2026, 8, 11)])

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_IsOK가_문자열_false여도_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        """IsOK 응답값의 실제 타입(boolean/문자열)은 raw 응답으로 검증하지 못했으므로
        문자열 "false"로 내려오는 경우도 함께 방어한다."""
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'IsOK': 'false', 'ErrorMessage': '일시적인 오류'}
        mock_post.return_value = response

        with pytest.raises(CinemaCrawlerError):
            crawler.get_open_dates_bulk(movie_codes=['24329'], candidate_dates=[date(2026, 8, 11)])
