import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.cinema.crawlers.base import CinemaCrawlerError
from apps.cinema.crawlers.lotte import LotteJamsilSuperplexCrawler

# 아래 픽스처는 실제 브라우저 세션 HAR 캡처(GetPlaySequence, representationMovieCode="")에서
# 그대로 가져온 필드 구성이다(행 수만 축약). 이 호출 하나로 그 극장·날짜의 모든 영화·모든
# 상영관 회차가 함께 반환된다는 것이 실제로 확인되었다.

_ALL_SESSIONS_RESPONSE = {
    'IsOK': 'true',
    'PlaySeqs': {'Items': [
        {
            'ScreenDivisionNameKR': '수퍼플렉스', 'ScreenDivisionCode': 940,
            'ScreenID': 101621, 'ScreenNameKR': '21관',
            'CinemaID': 1016, 'PlayDt': '2026-08-12',
            'RepresentationMovieCode': '24128', 'MovieCode': '24642', 'MovieNameKR': '오디세이',
            'StartTime': '10:30', 'EndTime': '13:32',
            'TotalSeatCount': 295, 'BookingSeatCount': 124,
        },
        {
            'ScreenDivisionNameKR': '수퍼플렉스', 'ScreenDivisionCode': 940,
            'ScreenID': 101621, 'ScreenNameKR': '21관',
            'CinemaID': 1016, 'PlayDt': '2026-08-12',
            'RepresentationMovieCode': '24128', 'MovieCode': '24642', 'MovieNameKR': '오디세이',
            'StartTime': '15:00', 'EndTime': '18:02',
            'TotalSeatCount': 295, 'BookingSeatCount': 40,
        },
        {
            'ScreenDivisionNameKR': '수퍼플렉스', 'ScreenDivisionCode': 940,
            'ScreenID': 101621, 'ScreenNameKR': '21관',
            'CinemaID': 1016, 'PlayDt': '2026-08-12',
            'RepresentationMovieCode': '24329', 'MovieCode': '24634', 'MovieNameKR': '스파이더맨: 브랜드 뉴 데이',
            'StartTime': '08:00', 'EndTime': '10:35',
            'TotalSeatCount': 295, 'BookingSeatCount': 203,
        },
        {
            # 같은 극장의 다른 상영관(샤롯데) 회차 — 수퍼플렉스가 아니므로 걸러야 한다.
            'ScreenDivisionNameKR': '샤롯데', 'ScreenDivisionCode': 300,
            'ScreenID': 1202, 'ScreenNameKR': '2관 샤롯데',
            'CinemaID': 1016, 'PlayDt': '2026-08-12',
            'RepresentationMovieCode': '24128', 'MovieCode': '24642', 'MovieNameKR': '오디세이',
            'StartTime': '13:00', 'EndTime': '16:02',
            'TotalSeatCount': 32, 'BookingSeatCount': 0,
        },
    ]},
}


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


@pytest.fixture
def crawler() -> LotteJamsilSuperplexCrawler:
    return LotteJamsilSuperplexCrawler()


class TestCall:
    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_실제_브라우저_요청에_포함되는_공통_파라미터와_Referer를_함께_보낸다(self, mock_post, crawler) -> None:
        """HAR 캡처로 확인된 실제 GetPlaySequence 요청은 MethodName 외에 channelType/osType/
        osVersion을 항상 포함하고(memberOnNo는 GetTicketingPageTOBE 요청에만 있어 포함하지
        않는다) Referer 헤더를 보낸다 — 최대한 실제 트래픽에 맞춘다."""
        mock_post.return_value = _mock_response({'IsOK': 'true', 'PlaySeqs': {'Items': []}})

        crawler._fetch_superplex_sessions_for_date(date(2026, 8, 12))

        payload = json.loads(mock_post.call_args.kwargs['files']['paramList'][1])
        assert payload['channelType'] == 'HO'
        assert payload['osType'] == 'W'
        assert 'osVersion' in payload
        assert 'memberOnNo' not in payload
        assert payload['representationMovieCode'] == ''
        assert mock_post.call_args.kwargs['headers']['Referer'] == 'https://www.lottecinema.co.kr/NLCHS/Ticketing'


class TestListNowShowing:
    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_수퍼플렉스_회차가_있는_영화만_중복없이_반환한다(self, mock_post, crawler) -> None:
        mock_post.return_value = _mock_response(_ALL_SESSIONS_RESPONSE)

        result = crawler.list_now_showing(reference_date=date(2026, 8, 12))

        assert {item.movie_code for item in result} == {'24128', '24329'}
        titles = {item.movie_code: item.title for item in result}
        assert titles['24128'] == '오디세이'
        assert titles['24329'] == '스파이더맨: 브랜드 뉴 데이'

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_기준일_당일에_회차가_없어도_발견_기간_내면_발견한다(self, mock_post, crawler) -> None:
        """개봉 예정작처럼 기준일 당일엔 회차가 없고 며칠 뒤부터 열리는 영화도, 발견 기간
        (_DISCOVERY_WINDOW_DAYS) 안이라면 list_now_showing이 놓치지 않아야 한다."""
        future_only_response = {
            'IsOK': 'true',
            'PlaySeqs': {'Items': [{
                'ScreenDivisionNameKR': '수퍼플렉스', 'ScreenDivisionCode': 940,
                'CinemaID': 1016, 'PlayDt': '2026-08-14',
                'RepresentationMovieCode': '99999', 'MovieCode': '99999', 'MovieNameKR': '개봉예정작',
                'StartTime': '10:00', 'EndTime': '12:00',
            }]},
        }

        def _side_effect(*args, **kwargs):
            payload = json.loads(kwargs['files']['paramList'][1])
            if payload['playDate'] == '2026-08-14':
                return _mock_response(future_only_response)
            return _mock_response({'IsOK': 'true', 'PlaySeqs': {'Items': []}})

        mock_post.side_effect = _side_effect

        result = crawler.list_now_showing(reference_date=date(2026, 8, 12))

        assert {item.movie_code for item in result} == {'99999'}
        assert mock_post.call_count == 3

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_요청_실패시_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        mock_post.side_effect = requests.ConnectionError('boom')

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 8, 12))

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_응답이_dict가_아니면_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        mock_post.return_value = _mock_response(['unexpected', 'shape'])

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 8, 12))

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_IsOK가_False면_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        mock_post.return_value = _mock_response({'IsOK': False, 'ErrorMessage': '일시적인 오류'})

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 8, 12))

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_IsOK가_문자열_false여도_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        """IsOK는 라이브 응답으로 문자열 "true"임이 확인됐다(HAR) — 실패 시 문자열 "false"로
        내려올 가능성도 함께 방어한다(HAR에 실패 사례가 없어 이 표현 자체는 추정)."""
        mock_post.return_value = _mock_response({'IsOK': 'false', 'ErrorMessage': '일시적인 오류'})

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing(reference_date=date(2026, 8, 12))


class TestGetOpenDatesBulk:
    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_감시중인_영화의_수퍼플렉스_상영시간만_모아_반환한다(self, mock_post, crawler) -> None:
        mock_post.return_value = _mock_response(_ALL_SESSIONS_RESPONSE)

        result = crawler.get_open_dates_bulk(
            movie_codes=['24128', '24329'], candidate_dates=[date(2026, 8, 12)],
        )

        assert result['24128'][date(2026, 8, 12)] == ['10:30', '15:00']
        assert result['24329'][date(2026, 8, 12)] == ['08:00']

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_감시중이지_않은_영화나_수퍼플렉스가_아닌_회차는_결과에_없다(self, mock_post, crawler) -> None:
        mock_post.return_value = _mock_response(_ALL_SESSIONS_RESPONSE)

        result = crawler.get_open_dates_bulk(
            movie_codes=['아직_안_열린_영화'], candidate_dates=[date(2026, 8, 12)],
        )

        assert result['아직_안_열린_영화'] == {}

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_후보_날짜마다_1콜만_보낸다(self, mock_post, crawler) -> None:
        """영화별이 아니라 날짜별로 1콜만 보내는지 확인한다 — 감시 영화가 여러 개여도
        요청 수가 늘지 않아야 한다."""
        mock_post.return_value = _mock_response(_ALL_SESSIONS_RESPONSE)

        crawler.get_open_dates_bulk(
            movie_codes=['24128', '24329'],
            candidate_dates=[date(2026, 8, 12), date(2026, 8, 13)],
        )

        assert mock_post.call_count == 2

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_IsOK가_False면_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        mock_post.return_value = _mock_response({'IsOK': False, 'ErrorMessage': '일시적인 오류'})

        with pytest.raises(CinemaCrawlerError):
            crawler.get_open_dates_bulk(movie_codes=['24128'], candidate_dates=[date(2026, 8, 12)])

    @patch('apps.cinema.crawlers.lotte.requests.post')
    def test_요청_실패시_CinemaCrawlerError를_발생시킨다(self, mock_post, crawler) -> None:
        mock_post.side_effect = requests.ConnectionError('boom')

        with pytest.raises(CinemaCrawlerError):
            crawler.get_open_dates_bulk(movie_codes=['24128'], candidate_dates=[date(2026, 8, 12)])


class TestBuildBookingUrl:
    def test_영화가_선택된_예매_화면_URL을_반환한다(self, crawler) -> None:
        """롯데 예매 화면은 CGV와 달리 URL 쿼리 파라미터로 상태를 받는다 — 새 탭에 직접
        붙여넣는 콜드 접속에도 영화가 이미 선택된 상태로 열리는 것을 실측 확인했다(스펙
        문서 참고)."""
        url = crawler.build_booking_url('24128', '오디세이')

        assert url == (
            'https://www.lottecinema.co.kr/NLCHS/ticketing'
            '?movieCd=24128&movieName=%EC%98%A4%EB%94%94%EC%84%B8%EC%9D%B4'
        )
