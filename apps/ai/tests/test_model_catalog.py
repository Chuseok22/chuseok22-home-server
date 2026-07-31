from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.ai.services.model_catalog import get_model_choices
from apps.ai.services.suh_aider_client import SuhAiderClientError


@override_settings(SUH_AIDER_BASE_URL='https://ai.example.com', SUH_AIDER_API_KEY='test-api-key')
class TestGetModelChoices(TestCase):
    def setUp(self) -> None:
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    @patch('apps.ai.services.model_catalog.SuhAiderClient')
    def test_completion_모델과_임베딩_모델을_그룹으로_분류한다(self, mock_client_cls: MagicMock) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.list_models.return_value = [
            {'name': 'functiongemma:latest', 'details': {'parameter_size': '268.10M'}},
            {'name': 'qwen3-embedding:4b', 'details': {'parameter_size': '4.0B'}},
        ]
        mock_client.get_model_capabilities.side_effect = lambda name: (
            ['completion', 'tools'] if name == 'functiongemma:latest' else ['tools', 'embedding']
        )

        result = get_model_choices()

        self.assertEqual(
            result,
            [
                ('채팅용', [('functiongemma:latest', 'functiongemma:latest (268.10M)')]),
                ('기타 (임베딩 등)', [('qwen3-embedding:4b', 'qwen3-embedding:4b (4.0B)')]),
            ],
        )

    @patch('apps.ai.services.model_catalog.SuhAiderClient')
    def test_캐시_히트시_SUH_AIder를_재호출하지_않는다(self, mock_client_cls: MagicMock) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.list_models.return_value = [
            {'name': 'functiongemma:latest', 'details': {'parameter_size': '268.10M'}},
        ]
        mock_client.get_model_capabilities.return_value = ['completion']

        first = get_model_choices()
        second = get_model_choices()

        self.assertEqual(first, second)
        mock_client.list_models.assert_called_once()

    @patch('apps.ai.services.model_catalog.SuhAiderClient')
    def test_일부_모델_capabilities_조회_실패시_해당_모델만_제외한다(self, mock_client_cls: MagicMock) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.list_models.return_value = [
            {'name': 'functiongemma:latest', 'details': {'parameter_size': '268.10M'}},
            {'name': 'broken-model:latest', 'details': {'parameter_size': '1B'}},
        ]

        def capabilities_side_effect(name: str) -> list[str]:
            if name == 'broken-model:latest':
                raise SuhAiderClientError('boom')
            return ['completion']

        mock_client.get_model_capabilities.side_effect = capabilities_side_effect

        result = get_model_choices()

        self.assertEqual(
            result, [('채팅용', [('functiongemma:latest', 'functiongemma:latest (268.10M)')])]
        )

    @patch('apps.ai.services.model_catalog.SuhAiderClient')
    def test_전체_목록_조회_실패시_빈_리스트를_반환한다(self, mock_client_cls: MagicMock) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.list_models.side_effect = SuhAiderClientError('연결 실패')

        result = get_model_choices()

        self.assertEqual(result, [])

    @patch('apps.ai.services.model_catalog.SuhAiderClient')
    def test_개별_capabilities_조회가_전부_실패하면_빈_리스트를_캐싱하지_않는다(
        self, mock_client_cls: MagicMock
    ) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.list_models.return_value = [
            {'name': 'functiongemma:latest', 'details': {'parameter_size': '268.10M'}},
        ]
        mock_client.get_model_capabilities.side_effect = SuhAiderClientError('boom')

        first = get_model_choices()
        second = get_model_choices()

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        # 캐시됐다면 두 번째 호출은 list_models()를 다시 부르지 않았을 것이다 — 재시도됐는지 확인.
        self.assertEqual(mock_client.list_models.call_count, 2)

    @patch('apps.ai.services.model_catalog.SuhAiderClient')
    def test_name_키가_없는_모델은_skip한다(self, mock_client_cls: MagicMock) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.list_models.return_value = [
            {'name': 'functiongemma:latest', 'details': {'parameter_size': '268.10M'}},
            {'details': {'parameter_size': '1B'}},  # name 키 없음
        ]
        mock_client.get_model_capabilities.return_value = ['completion']

        result = get_model_choices()

        self.assertEqual(
            result, [('채팅용', [('functiongemma:latest', 'functiongemma:latest (268.10M)')])]
        )
