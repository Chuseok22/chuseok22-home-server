import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.models import PromptTemplate
from apps.ai.services.suh_aider_client import SuhAiderClientError
from apps.clubs.services.llm_recruitment_detector import detect_recruitment

_PAGE_TEXT = 'SOPT 35기 모집 안내. 35기 지원 기간: 2026.09.01 ~ 09.14. 많은 지원 바랍니다.'


def _make_active_prompt(model: str = 'functiongemma') -> PromptTemplate:
    return PromptTemplate.objects.create(
        feature='club_recruitment_detection', name='테스트 프롬프트',
        system_prompt='시스템 프롬프트', model=model, is_active=True,
    )


@override_settings(SUH_AIDER_BASE_URL='https://ai.example.com', SUH_AIDER_API_KEY='test-key')
class TestDetectRecruitment(TestCase):
    def test_활성_프롬프트가_없으면_None을_반환한다(self) -> None:
        assert detect_recruitment('SOPT', _PAGE_TEXT) is None

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_정상_JSON_응답이면_모집중으로_판별한다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': True,
            'application_start': '2026-09-01',
            'application_end': '2026-09-14',
            'apply_url': 'https://www.sopt.org/apply',
            'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is True
        assert result.application_start.isoformat() == '2026-09-01'
        assert result.application_end.isoformat() == '2026-09-14'
        assert result.apply_url == 'https://www.sopt.org/apply'

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_evidence_quote가_원문에_없으면_grounding_실패로_모집중아님_처리한다(
        self, mock_chat: MagicMock,
    ) -> None:
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': True,
            'application_start': '2026-09-01',
            'application_end': '2026-09-14',
            'apply_url': None,
            'evidence_quote': '이 문장은 원문에 없습니다',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is False

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_시작일이_종료일보다_늦으면_모집중아님으로_낮춘다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': True,
            'application_start': '2026-09-14',
            'application_end': '2026-09-01',
            'apply_url': None,
            'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result.is_recruiting is False

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_종료일이_비정상적으로_먼_미래면_모집중아님으로_낮춘다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        far_future = (timezone.localdate() + timedelta(days=500)).isoformat()
        mock_chat.return_value = json.dumps({
            'is_recruiting': True,
            'application_start': None,
            'application_end': far_future,
            'apply_url': None,
            'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result.is_recruiting is False

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_모집중이_아니라고_판별하면_그대로_반환한다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': False,
            'application_start': None,
            'application_end': None,
            'apply_url': None,
            'evidence_quote': None,
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is False

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_JSON_앞뒤에_설명이_붙어있어도_블록만_추출해_파싱한다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.return_value = (
            '다음은 판별 결과입니다:\n'
            + json.dumps({
                'is_recruiting': True,
                'application_start': '2026-09-01',
                'application_end': '2026-09-14',
                'apply_url': None,
                'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
            })
            + '\n이상입니다.'
        )

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is True

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_완전히_파싱불가능한_응답이면_None을_반환한다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.return_value = '판별할 수 없습니다.'

        assert detect_recruitment('SOPT', _PAGE_TEXT) is None

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_JSON이지만_dict가_아니면_None을_반환한다(self, mock_chat: MagicMock) -> None:
        # LLM이 JSON 배열/문자열 등 유효하지만 dict가 아닌 JSON을 반환하는 경우 — parsed.get(...)
        # 호출 시 AttributeError로 죽지 않고 판별 실패(None)로 처리돼야 한다.
        _make_active_prompt()
        mock_chat.return_value = json.dumps(['is_recruiting', True])

        assert detect_recruitment('SOPT', _PAGE_TEXT) is None

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_SUH_AIder_호출_실패시_None을_반환한다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.side_effect = SuhAiderClientError('연결 실패')

        assert detect_recruitment('SOPT', _PAGE_TEXT) is None

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_apply_url이_200자를_초과하면_URL만_비우고_모집중은_유지한다(self, mock_chat: MagicMock) -> None:
        long_url = 'https://www.sopt.org/apply?' + 'a' * 230
        assert len(long_url) > 200
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': True,
            'application_start': '2026-09-01',
            'application_end': '2026-09-14',
            'apply_url': long_url,
            'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is True
        assert result.apply_url == ''

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_apply_url이_http_https가_아니면_URL만_비우고_모집중은_유지한다(self, mock_chat: MagicMock) -> None:
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': True,
            'application_start': '2026-09-01',
            'application_end': '2026-09-14',
            'apply_url': 'javascript:alert(1)',
            'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is True
        assert result.apply_url == ''

    @patch('apps.clubs.services.llm_recruitment_detector.SuhAiderClient.chat')
    def test_is_recruiting이_문자열_false면_JSON_boolean이_아니므로_모집중아님으로_처리한다(
        self, mock_chat: MagicMock,
    ) -> None:
        # LLM이 is_recruiting을 문자열 "false"로 반환하는 경우 — bool("false") = True 함정을 피하기 위해
        # 정확히 JSON boolean true만 인정한다.
        _make_active_prompt()
        mock_chat.return_value = json.dumps({
            'is_recruiting': 'false',  # 문자열, boolean이 아님
            'application_start': None,
            'application_end': None,
            'apply_url': None,
            'evidence_quote': '35기 지원 기간: 2026.09.01 ~ 09.14',
        })

        result = detect_recruitment('SOPT', _PAGE_TEXT)

        assert result is not None
        assert result.is_recruiting is False
