from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import CHATBOT_FEATURE

_PROMPT_NAME = '기본 챗봇 프롬프트'


class TestSeedChatbotPrompt(TestCase):
    def test_레코드가_없으면_새로_생성하고_활성화한다(self) -> None:
        call_command('seed_chatbot_prompt', stdout=StringIO())

        template = PromptTemplate.objects.get(feature=CHATBOT_FEATURE, name=_PROMPT_NAME)
        self.assertTrue(template.is_active)
        self.assertEqual(template.model, 'functiongemma')
        self.assertIn('대표 프로젝트 추천', template.system_prompt)
        self.assertIn('연락처', template.system_prompt)

    def test_model_옵션으로_생성_시_모델명을_지정할_수_있다(self) -> None:
        call_command('seed_chatbot_prompt', model='다른모델', stdout=StringIO())

        template = PromptTemplate.objects.get(feature=CHATBOT_FEATURE, name=_PROMPT_NAME)
        self.assertEqual(template.model, '다른모델')

    def test_이미_있으면_system_prompt만_갱신하고_model은_보존한다(self) -> None:
        PromptTemplate.objects.create(
            feature=CHATBOT_FEATURE, name=_PROMPT_NAME,
            system_prompt='이전 문구', model='운영에서-고른-모델', is_active=False,
        )

        call_command('seed_chatbot_prompt', stdout=StringIO())

        template = PromptTemplate.objects.get(feature=CHATBOT_FEATURE, name=_PROMPT_NAME)
        self.assertEqual(template.model, '운영에서-고른-모델')
        self.assertTrue(template.is_active)
        self.assertIn('대표 프로젝트 추천', template.system_prompt)
        self.assertNotEqual(template.system_prompt, '이전 문구')

    def test_다른_이름의_커스텀_프롬프트는_비활성화되지만_내용은_보존된다(self) -> None:
        custom = PromptTemplate.objects.create(
            feature=CHATBOT_FEATURE, name='커스텀 실험 프롬프트',
            system_prompt='실험용 문구', model='functiongemma', is_active=True,
        )

        call_command('seed_chatbot_prompt', stdout=StringIO())

        custom.refresh_from_db()
        self.assertFalse(custom.is_active)
        self.assertEqual(custom.system_prompt, '실험용 문구')
        new_template = PromptTemplate.objects.get(feature=CHATBOT_FEATURE, name=_PROMPT_NAME)
        self.assertTrue(new_template.is_active)

    def test_재실행해도_레코드_개수가_늘지_않는다(self) -> None:
        call_command('seed_chatbot_prompt', stdout=StringIO())
        call_command('seed_chatbot_prompt', stdout=StringIO())

        self.assertEqual(
            PromptTemplate.objects.filter(feature=CHATBOT_FEATURE, name=_PROMPT_NAME).count(), 1,
        )
