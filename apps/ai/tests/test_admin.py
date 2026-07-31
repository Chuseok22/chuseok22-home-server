from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.ai.admin import PromptTemplateForm
from apps.ai.models import PromptTemplate


class TestPromptTemplateForm(TestCase):
    @patch('apps.ai.admin.get_model_choices')
    def test_모델_선택지가_채워진다(self, mock_get_choices: MagicMock) -> None:
        mock_get_choices.return_value = [
            ('채팅용', [('functiongemma:latest', 'functiongemma:latest (268.10M)')]),
        ]

        form = PromptTemplateForm()

        self.assertEqual(
            form.fields['model'].choices,
            [('채팅용', [('functiongemma:latest', 'functiongemma:latest (268.10M)')])],
        )

    @patch('apps.ai.admin.get_model_choices')
    def test_기존_모델_값이_목록에_없어도_유효하다(self, mock_get_choices: MagicMock) -> None:
        mock_get_choices.return_value = [
            ('채팅용', [('functiongemma:latest', 'functiongemma:latest (268.10M)')]),
        ]
        instance = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='기존',
            system_prompt='기존 프롬프트',
            model='deprecated-model:latest',
            is_active=False,
        )

        form = PromptTemplateForm(
            data={
                'feature': PromptTemplate.Feature.CHATBOT,
                'name': '기존',
                'system_prompt': '기존 프롬프트',
                'model': 'deprecated-model:latest',
                'is_active': False,
            },
            instance=instance,
        )

        self.assertTrue(form.is_valid(), form.errors)

    @patch('apps.ai.admin.get_model_choices')
    def test_모델_목록_조회_실패시_안내_문구가_표시된다(self, mock_get_choices: MagicMock) -> None:
        mock_get_choices.return_value = []

        form = PromptTemplateForm()

        # ChoiceField의 help_text 기본값은 None이 아니라 빈 문자열('')이므로,
        # None 여부가 아니라 실제 안내 문구가 들어갔는지로 검증해야 의미가 있다.
        self.assertIn('연결할 수 없어', form.fields['model'].help_text)
