from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.certifications.crawlers.hrdkorea_api import HrdKoreaApiCrawler, _parse_date

_SUCCESS_RESPONSE = {
    'response': {
        'header': {'resultCode': '00', 'resultMsg': 'NORMAL SERVICE'},
        'body': {
            'items': {
                'item': [
                    {
                        'implYy': '2026', 'implSeq': '1', 'qualgbCd': 'T', 'qualgbNm': '국가기술자격',
                        'description': '정보처리기사',
                        'docRegStartDt': '20260105', 'docRegEndDt': '20260109',
                        'docExamStartDt': '20260207', 'docExamEndDt': '20260207', 'docPassDt': '20260304',
                        'pracRegStartDt': '20260401', 'pracRegEndDt': '20260405',
                        'pracExamStartDt': '20260523', 'pracExamEndDt': '20260609', 'pracPassDt': '20260626',
                    },
                ],
            },
            'numOfRows': 100, 'pageNo': 1, 'totalCount': 1,
        },
    },
}

_EMPTY_RESPONSE = {
    'response': {
        'header': {'resultCode': '00', 'resultMsg': 'NORMAL SERVICE'},
        'body': {'items': '', 'numOfRows': 100, 'pageNo': 1, 'totalCount': 0},
    },
}


def test_parse_date는_YYYYMMDD를_변환한다() -> None:
    assert _parse_date('20260105') == date(2026, 1, 5)


def test_parse_date는_빈값에_None을_반환한다() -> None:
    assert _parse_date('') is None
    assert _parse_date(None) is None


def test_parse_date는_잘못된_형식에_None을_반환한다() -> None:
    assert _parse_date('2026-01-05') is None


@override_settings(HRD_KOREA_API_KEY='test-key')
class TestHrdKoreaApiCrawlerCrawl(TestCase):
    def test_필기_실기_두_회차로_분리해서_반환한다(self) -> None:
        crawler = HrdKoreaApiCrawler()

        with patch('apps.certifications.crawlers.hrdkorea_api.requests.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=_SUCCESS_RESPONSE),
            )
            mock_get.return_value.raise_for_status.return_value = None
            result = crawler._crawl_year('1320', 2026)

        assert len(result) == 2
        written, practical = result
        assert written.round_name == '2026년 1회 필기'
        assert written.registration_start == date(2026, 1, 5)
        assert written.registration_end == date(2026, 1, 9)
        assert written.exam_date == date(2026, 2, 7)
        assert written.result_announcement_date == date(2026, 3, 4)
        assert practical.round_name == '2026년 1회 실기'
        assert practical.registration_start == date(2026, 4, 1)

    def test_응답이_비어있으면_빈_리스트를_반환한다(self) -> None:
        crawler = HrdKoreaApiCrawler()

        with patch('apps.certifications.crawlers.hrdkorea_api.requests.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=_EMPTY_RESPONSE),
            )
            mock_get.return_value.raise_for_status.return_value = None
            result = crawler._crawl_year('1320', 2026)

        assert result == []

    def test_resultCode가_실패면_빈_리스트를_반환하고_예외를_던지지_않는다(self) -> None:
        crawler = HrdKoreaApiCrawler()
        error_response = {
            'response': {'header': {'resultCode': '99', 'resultMsg': 'SERVICE ERROR'}, 'body': {}},
        }

        with patch('apps.certifications.crawlers.hrdkorea_api.requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=error_response))
            mock_get.return_value.raise_for_status.return_value = None
            result = crawler._crawl_year('1320', 2026)

        assert result == []

    def test_네트워크_오류시_빈_리스트를_반환하고_예외를_던지지_않는다(self) -> None:
        import requests

        crawler = HrdKoreaApiCrawler()

        with patch('apps.certifications.crawlers.hrdkorea_api.requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError('연결 실패')
            result = crawler._crawl_year('1320', 2026)

        assert result == []


@override_settings(HRD_KOREA_API_KEY='')
class TestHrdKoreaApiCrawlerMissingApiKey(TestCase):
    def test_API_키_미설정시_API를_호출하지_않고_빈_리스트를_반환한다(self) -> None:
        crawler = HrdKoreaApiCrawler()

        with patch('apps.certifications.crawlers.hrdkorea_api.requests.get') as mock_get:
            result = crawler.crawl('1320')

        assert result == []
        mock_get.assert_not_called()
