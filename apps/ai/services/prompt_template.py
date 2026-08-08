from apps.ai.models import PromptTemplate

CHATBOT_FEATURE = PromptTemplate.Feature.CHATBOT
GITHUB_TRENDING_SUMMARY_FEATURE = PromptTemplate.Feature.GITHUB_TRENDING_SUMMARY


def get_active_prompt(feature: str) -> PromptTemplate | None:
    """주어진 feature의 활성 프롬프트를 반환한다. 없으면 None."""
    return PromptTemplate.objects.filter(feature=feature, is_active=True).first()
