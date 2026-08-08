from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import GITHUB_TRENDING_SUMMARY_FEATURE

_PROMPT_NAME = 'GitHub 트렌딩 요약 프롬프트'


class TestSeedGithubTrendingSummaryPrompt(TestCase):
    def test_레코드가_없으면_새로_생성하고_활성화한다(self) -> None:
        call_command('seed_github_trending_summary_prompt', stdout=StringIO())

        template = PromptTemplate.objects.get(feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME)
        self.assertTrue(template.is_active)
        self.assertEqual(template.model, 'functiongemma')
        self.assertIn('한국어', template.system_prompt)

    def test_model_옵션으로_생성_시_모델명을_지정할_수_있다(self) -> None:
        call_command('seed_github_trending_summary_prompt', model='다른모델', stdout=StringIO())

        template = PromptTemplate.objects.get(feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME)
        self.assertEqual(template.model, '다른모델')

    def test_이미_있으면_system_prompt만_갱신하고_model은_보존한다(self) -> None:
        PromptTemplate.objects.create(
            feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME,
            system_prompt='이전 문구', model='운영에서-고른-모델', is_active=False,
        )

        call_command('seed_github_trending_summary_prompt', stdout=StringIO())

        template = PromptTemplate.objects.get(feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME)
        self.assertEqual(template.model, '운영에서-고른-모델')
        self.assertTrue(template.is_active)
        self.assertNotEqual(template.system_prompt, '이전 문구')

    def test_재실행해도_레코드_개수가_늘지_않는다(self) -> None:
        call_command('seed_github_trending_summary_prompt', stdout=StringIO())
        call_command('seed_github_trending_summary_prompt', stdout=StringIO())

        self.assertEqual(
            PromptTemplate.objects.filter(feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME).count(), 1,
        )
