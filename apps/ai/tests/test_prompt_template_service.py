from django.test import TestCase

from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import CHATBOT_FEATURE, get_active_prompt, GITHUB_TRENDING_SUMMARY_FEATURE


class TestGetActivePrompt(TestCase):
    def test_활성_프롬프트가_있으면_반환한다(self) -> None:
        PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='비활성',
            system_prompt='...',
            model='functiongemma',
            is_active=False,
        )
        active = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='활성',
            system_prompt='활성 프롬프트',
            model='functiongemma',
            is_active=True,
        )

        result = get_active_prompt(CHATBOT_FEATURE)

        self.assertEqual(result, active)

    def test_활성_프롬프트가_없으면_None을_반환한다(self) -> None:
        result = get_active_prompt(CHATBOT_FEATURE)

        self.assertIsNone(result)

    def test_CHATBOT_FEATURE는_PromptTemplate_Feature_CHATBOT과_같은_값이다(self) -> None:
        self.assertEqual(CHATBOT_FEATURE, PromptTemplate.Feature.CHATBOT)


class TestGithubTrendingSummaryFeature(TestCase):
    def test_github_trending_summary_feature_상수값(self) -> None:
        self.assertEqual(GITHUB_TRENDING_SUMMARY_FEATURE, PromptTemplate.Feature.GITHUB_TRENDING_SUMMARY)
        self.assertEqual(PromptTemplate.Feature.GITHUB_TRENDING_SUMMARY, 'github_trending_summary')

    def test_해당_feature로_활성_프롬프트_조회(self) -> None:
        PromptTemplate.objects.create(
            feature=GITHUB_TRENDING_SUMMARY_FEATURE, name='트렌딩 요약 프롬프트',
            system_prompt='요약해줘', model='functiongemma', is_active=True,
        )
        result = get_active_prompt(GITHUB_TRENDING_SUMMARY_FEATURE)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, '트렌딩 요약 프롬프트')
