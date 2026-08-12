from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.cinema.crawlers.base import CinemaCrawlerError
from apps.cinema.crawlers.cgv import CgvYongsanImaxCrawler

# 아래 픽스처는 실제 브라우저 세션 HAR 캡처에서 그대로 가져온 필드 구성이다(값만 축약).

_TOP_MOVIES_RESPONSE = {
    'statusCode': 0,
    'data': [
        {'coCd': 'A420', 'movNo': '30001323', 'movNm': '오디세이'},
        {'coCd': 'A420', 'movNo': '30001192', 'movNm': '스파이더맨-브랜드 뉴 데이'},
    ],
}


def _schedule_count_response(imax_sites: list[str], gold_class_sites: list[str] | None = None) -> dict:
    return {
        'statusCode': 0,
        'data': [
            {'comCd': 'TCSCNS_GRAD_CD', 'comCdval': '04', 'comCdvalNm': 'SCREENX', 'sscnsSiteList': []},
            {
                # 실제 HAR 응답에는 comCdval="03"이 comCd별로 서로 다른 의미(TCSCNS_GRAD_CD의
                # 03=아이맥스, SASCNS_GRAD_CD의 03=골드클래스)로 두 번 등장한다 — 골드클래스
                # 항목을 먼저 배치해 comCd를 함께 확인하지 않으면 오판하는 경로를 재현한다.
                'comCd': 'SASCNS_GRAD_CD', 'comCdval': '03', 'comCdvalNm': '골드클래스',
                'sscnsSiteList': [{'siteNo': site} for site in (gold_class_sites or [])],
            },
            {
                'comCd': 'TCSCNS_GRAD_CD', 'comCdval': '03', 'comCdvalNm': '아이맥스',
                'sscnsSiteList': [{'siteNo': site} for site in imax_sites],
            },
        ],
    }


_OPEN_DATES_RESPONSE = {
    'statusCode': 0,
    'data': [{'scnYmd': '20260812', 'hldyYn': None}, {'scnYmd': '20260825', 'hldyYn': None}],
}

_SCHEDULE_RESPONSE = {
    'statusCode': 0,
    'data': [
        {
            'coCd': 'A420', 'siteNo': '0013', 'siteNm': 'CGV 용산아이파크몰',
            'scnsNo': '018', 'scnsNm': 'IMAX관', 'scnYmd': '20260825',
            'scnsrtTm': '0700', 'scnendTm': '1002', 'movNo': '30001323', 'movNm': '오디세이',
        },
        {
            'coCd': 'A420', 'siteNo': '0013', 'siteNm': 'CGV 용산아이파크몰',
            'scnsNo': '018', 'scnsNm': 'IMAX관', 'scnYmd': '20260825',
            'scnsrtTm': '1030', 'scnendTm': '1332', 'movNo': '30001323', 'movNm': '오디세이',
        },
        {
            # 인접한 다른 브랜드관(씨네드쉐프 용산, siteNo=P013)의 회차 — 실제 응답에서
            # siteNo=0013으로 요청해도 함께 섞여 나오는 것이 확인되어, siteNo로도 걸러야 한다.
            'coCd': 'A420', 'siteNo': 'P013', 'siteNm': '씨네드쉐프 용산',
            'scnsNo': '001', 'scnsNm': '스트레스리스 시네마[CINE de CHEF]', 'scnYmd': '20260825',
            'scnsrtTm': '2250', 'scnendTm': '2547', 'movNo': '30001323', 'movNm': '오디세이',
        },
        {
            # 같은 사이트(0013)지만 IMAX가 아닌 일반관 회차 — scnsNm 기준으로도 걸러야 한다.
            'coCd': 'A420', 'siteNo': '0013', 'siteNm': 'CGV 용산아이파크몰',
            'scnsNo': '002', 'scnsNm': '2관 (Laser)', 'scnYmd': '20260825',
            'scnsrtTm': '1410', 'scnendTm': '1712', 'movNo': '30001323', 'movNm': '오디세이',
        },
    ],
}


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _dispatch(url: str, **kwargs) -> MagicMock:
    if 'searchAtktTopPostrList' in url:
        return _mock_response(_TOP_MOVIES_RESPONSE)
    if 'searchSscnsSchdCntList' in url:
        return _mock_response(_schedule_count_response(['0013', '0074']))
    if 'searchSiteScnscYmdListByMov' in url:
        return _mock_response(_OPEN_DATES_RESPONSE)
    if 'searchSchByMov' in url:
        return _mock_response(_SCHEDULE_RESPONSE)
    raise AssertionError(f'예상치 못한 URL: {url}')


@pytest.fixture
def crawler() -> CgvYongsanImaxCrawler:
    return CgvYongsanImaxCrawler()


class TestListNowShowing:
    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_상영관_IMAX에서_상영중인_영화만_반환한다(self, mock_get, crawler) -> None:
        def _side_effect(url, **kwargs):
            if 'searchAtktTopPostrList' in url:
                return _mock_response(_TOP_MOVIES_RESPONSE)
            if 'searchSscnsSchdCntList' in url:
                # 30001323(오디세이)만 용산(0013) IMAX 상영, 30001192는 다른 사이트에서만 상영
                is_odyssey = kwargs['params']['movNo'] == '30001323'
                sites = ['0013'] if is_odyssey else ['0074']
                return _mock_response(_schedule_count_response(sites))
            raise AssertionError(f'예상치 못한 URL: {url}')

        mock_get.side_effect = _side_effect

        result = crawler.list_now_showing()

        assert [item.movie_code for item in result] == ['30001323']
        assert result[0].title == '오디세이'

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_골드클래스만_상영중이면_IMAX로_오판하지_않는다(self, mock_get, crawler) -> None:
        """comCdval="03"은 comCd에 따라 IMAX(TCSCNS_GRAD_CD)와 골드클래스(SASCNS_GRAD_CD) 둘 다에
        쓰인다 — comCd를 함께 확인하지 않으면 골드클래스만 상영 중인 영화를 IMAX 상영으로
        오판할 수 있다."""
        def _side_effect(url, **kwargs):
            if 'searchAtktTopPostrList' in url:
                return _mock_response(_TOP_MOVIES_RESPONSE)
            if 'searchSscnsSchdCntList' in url:
                # 두 영화 모두 골드클래스는 0013에서 상영하지만 IMAX는 상영하지 않는다.
                return _mock_response(_schedule_count_response(imax_sites=[], gold_class_sites=['0013']))
            raise AssertionError(f'예상치 못한 URL: {url}')

        mock_get.side_effect = _side_effect

        result = crawler.list_now_showing()

        assert result == []

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_요청_실패시_CinemaCrawlerError를_발생시킨다(self, mock_get, crawler) -> None:
        mock_get.side_effect = requests.ConnectionError('boom')

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing()

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_data가_리스트가_아니면_CinemaCrawlerError를_발생시킨다(self, mock_get, crawler) -> None:
        mock_get.return_value = _mock_response({'statusCode': 0, 'data': {'unexpected': 'shape'}})

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing()

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_응답_자체가_dict가_아니면_CinemaCrawlerError를_발생시킨다(self, mock_get, crawler) -> None:
        """이 API의 다른 필드(hldyYn 등)가 실제로 null을 내려보내는 것이 HAR로 확인되어,
        응답 최상위가 예상과 다른 형태(list 등)로 올 가능성도 방어해야 한다."""
        mock_get.return_value = _mock_response(['unexpected', 'shape'])

        with pytest.raises(CinemaCrawlerError):
            crawler.list_now_showing()


class TestGetOpenDatesBulk:
    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_후보_날짜와_열린_날짜의_교집합만_조회해_IMAX_회차를_모은다(self, mock_get, crawler) -> None:
        mock_get.side_effect = _dispatch

        result = crawler.get_open_dates_bulk(
            movie_codes=['30001323'], candidate_dates=[date(2026, 8, 25)],
        )

        assert result['30001323'][date(2026, 8, 25)] == ['07:00', '10:30']

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_다른_사이트나_IMAX가_아닌_회차는_제외한다(self, mock_get, crawler) -> None:
        mock_get.side_effect = _dispatch

        result = crawler.get_open_dates_bulk(
            movie_codes=['30001323'], candidate_dates=[date(2026, 8, 25)],
        )

        times = result['30001323'][date(2026, 8, 25)]
        assert '22:50' not in times  # 씨네드쉐프 용산(P013) 회차
        assert '14:10' not in times  # 같은 사이트의 일반관(2관) 회차

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_candidate_dates에_없는_열린_날짜는_조회하지_않는다(self, mock_get, crawler) -> None:
        mock_get.side_effect = _dispatch

        result = crawler.get_open_dates_bulk(
            movie_codes=['30001323'], candidate_dates=[date(2026, 8, 12)],
        )

        # 열린 날짜(20260812, 20260825) 중 후보에 없는 20260825는 조회 대상에서 빠져야 하므로
        # searchSchByMov가 20260812에 대해서만 호출된다.
        assert date(2026, 8, 25) not in result['30001323']

        scheduled_dates = [
            call.kwargs['params']['scnYmd']
            for call in mock_get.call_args_list
            if 'searchSchByMov' in call.args[0]
        ]
        assert scheduled_dates == ['20260812']

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_scnYmd가_null이어도_다른_날짜는_정상_처리한다(self, mock_get, crawler) -> None:
        """hldyYn처럼 이 API의 다른 필드가 실제로 null을 내려보내는 것이 HAR로 확인되어,
        scnYmd도 null일 가능성을 방어해야 한다 — 해당 행만 건너뛰고 나머지는 처리된다."""
        def _side_effect(url, **kwargs):
            if 'searchSiteScnscYmdListByMov' in url:
                return _mock_response({
                    'statusCode': 0,
                    'data': [{'scnYmd': None, 'hldyYn': None}, {'scnYmd': '20260812', 'hldyYn': None}],
                })
            if 'searchSchByMov' in url:
                return _mock_response(_SCHEDULE_RESPONSE)
            raise AssertionError(f'예상치 못한 URL: {url}')

        mock_get.side_effect = _side_effect

        result = crawler.get_open_dates_bulk(
            movie_codes=['30001323'], candidate_dates=[date(2026, 8, 12)],
        )

        assert date(2026, 8, 12) in result['30001323']

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_scnsNm이_null이어도_IMAX가_아닌_것으로_처리해_예외없이_필터링한다(self, mock_get, crawler) -> None:
        def _side_effect(url, **kwargs):
            if 'searchSiteScnscYmdListByMov' in url:
                return _mock_response(_OPEN_DATES_RESPONSE)
            if 'searchSchByMov' in url:
                return _mock_response({
                    'statusCode': 0,
                    'data': [{
                        'coCd': 'A420', 'siteNo': '0013', 'siteNm': 'CGV 용산아이파크몰',
                        'scnsNo': '018', 'scnsNm': None, 'scnYmd': '20260825',
                        'scnsrtTm': None, 'scnendTm': '1002', 'movNo': '30001323', 'movNm': '오디세이',
                    }],
                })
            raise AssertionError(f'예상치 못한 URL: {url}')

        mock_get.side_effect = _side_effect

        result = crawler.get_open_dates_bulk(
            movie_codes=['30001323'], candidate_dates=[date(2026, 8, 25)],
        )

        assert result['30001323'] == {}

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_감시중이지_않은_영화나_열리지_않은_날짜는_결과에_없다(self, mock_get, crawler) -> None:
        def _side_effect(url, **kwargs):
            if 'searchSiteScnscYmdListByMov' in url:
                return _mock_response({'statusCode': 0, 'data': []})
            raise AssertionError(f'예상치 못한 URL: {url}')

        mock_get.side_effect = _side_effect

        result = crawler.get_open_dates_bulk(
            movie_codes=['아직_안_열린_영화'], candidate_dates=[date(2026, 9, 10)],
        )

        assert result['아직_안_열린_영화'] == {}

    @patch('apps.cinema.crawlers.cgv.requests.get')
    def test_요청_실패시_CinemaCrawlerError를_발생시킨다(self, mock_get, crawler) -> None:
        mock_get.side_effect = requests.ConnectionError('boom')

        with pytest.raises(CinemaCrawlerError):
            crawler.get_open_dates_bulk(movie_codes=['30001323'], candidate_dates=[date(2026, 8, 25)])
