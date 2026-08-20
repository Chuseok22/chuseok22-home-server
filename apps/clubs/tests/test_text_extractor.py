from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase

from apps.clubs.services.text_extractor import fetch_page_text


class TestFetchPageText(SimpleTestCase):
    @patch('apps.clubs.services.text_extractor.requests.get')
    def test_정상_페이지에서_script_style_제외한_본문_텍스트를_반환한다(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # _MIN_TEXT_CHARS(200자) 가드를 통과하도록 본문을 충분히 길게 채운다 — 실제 모집
        # 공고 페이지가 소개문·활동 안내 등으로 200자를 훌쩍 넘는 것과 동일한 상황을 흉내낸다.
        body_paragraph = (
            'NEXTERS는 개발자와 디자이너가 함께 아이디어를 현실로 만드는 IT 연합 동아리입니다. '
            '13년간 800명 이상의 누적 활동 회원과 140개 이상의 서비스를 런칭했습니다. '
            '8주간 몰입하며 서비스 기획부터 검증, 출시까지 실제 프로덕트 개발 전 과정을 경험합니다. '
            '지난 기수 활동들을 통해 우리는 많은 경험을 쌓았고 더욱 성장했습니다.'
        )
        mock_response.text = (
            '<html><head><style>.a{color:red}</style></head>'
            '<body><script>console.log(1)</script>'
            f'<h1>NEXTERS 35기 모집</h1><p>{body_paragraph}</p>'
            '<p>지원 기간: 2026.09.01 ~ 09.14</p></body></html>'
        )
        mock_get.return_value = mock_response

        result = fetch_page_text('https://nexters.co.kr/')

        assert result is not None
        assert 'NEXTERS 35기 모집' in result
        assert '지원 기간' in result
        assert 'console.log' not in result
        assert 'color:red' not in result

    @patch('apps.clubs.services.text_extractor.requests.get')
    def test_본문이_비정상적으로_짧으면_None을_반환한다(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # SPA 셸만 응답하는 상황을 흉내낸다 — 실제 본문 없이 빈 div만 있는 경우
        mock_response.text = '<html><body><div id="root"></div></body></html>'
        mock_get.return_value = mock_response

        assert fetch_page_text('https://spa-example.com/') is None

    @patch('apps.clubs.services.text_extractor.requests.get')
    def test_요청_실패시_None을_반환한다(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError('연결 실패')

        assert fetch_page_text('https://unreachable.example.com/') is None

    @patch('apps.clubs.services.text_extractor.requests.get')
    def test_긴_본문은_MAX_TEXT_CHARS로_잘린다(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = f'<html><body><p>{"가" * 20000}</p></body></html>'
        mock_get.return_value = mock_response

        result = fetch_page_text('https://long-page.example.com/')

        assert result is not None
        assert len(result) == 8000
