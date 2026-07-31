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

    @patch('apps.ai.admin.get_model_choices')
    def test_기존_레코드에서_카탈로그_조회_실패시_안내_문구와_현재값이_모두_표시된다(
        self, mock_get_choices: MagicMock,
    ) -> None:
        # 기존에 저장된 모델이 있을 때 카탈로그 조회가 실패하는 경우
        mock_get_choices.return_value = []
        instance = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='기존',
            system_prompt='기존 프롬프트',
            model='deprecated-model:latest',
            is_active=False,
        )

        form = PromptTemplateForm(instance=instance)

        # 1. 안내 문구가 표시된다 (카탈로그 조회 실패)
        self.assertIn('연결할 수 없어', form.fields['model'].help_text)
        # 2. 현재값이 선택지에 포함된다 (기존 저장값 유지)
        # choices 구조: [('현재 값 (목록에 없음)', [('deprecated-model:latest', 'deprecated-model:latest')])]
        choices_list = form.fields['model'].choices
        # 첫 번째 그룹의 이름이 '현재 값 (목록에 없음)'인지 확인
        self.assertEqual(choices_list[0][0], '현재 값 (목록에 없음)')
        # 첫 번째 그룹의 옵션 리스트에 ('deprecated-model:latest', 'deprecated-model:latest')가 있는지 확인
        self.assertIn(('deprecated-model:latest', 'deprecated-model:latest'), choices_list[0][1])
