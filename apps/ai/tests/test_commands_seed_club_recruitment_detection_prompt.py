import pytest
from django.core.management import call_command

from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import CLUB_RECRUITMENT_DETECTION_FEATURE


@pytest.mark.django_db
def test_최초_실행시_활성_프롬프트를_생성한다() -> None:
    call_command('seed_club_recruitment_detection_prompt')

    template = PromptTemplate.objects.get(
        feature=CLUB_RECRUITMENT_DETECTION_FEATURE, is_active=True,
    )
    assert 'is_recruiting' in template.system_prompt
    assert 'evidence_quote' in template.system_prompt
    assert template.model == 'gemma4:e4b'


@pytest.mark.django_db
def test_model_옵션을_지정하면_새_레코드에_반영된다() -> None:
    call_command('seed_club_recruitment_detection_prompt', model='gemma3-4b')

    template = PromptTemplate.objects.get(
        feature=CLUB_RECRUITMENT_DETECTION_FEATURE, is_active=True,
    )
    assert template.model == 'gemma3-4b'


@pytest.mark.django_db
def test_이미_존재하면_문구만_갱신하고_model은_보존한다() -> None:
    call_command('seed_club_recruitment_detection_prompt', model='gemma3-4b')

    call_command('seed_club_recruitment_detection_prompt', model='다른모델')

    templates = PromptTemplate.objects.filter(feature=CLUB_RECRUITMENT_DETECTION_FEATURE)
    assert templates.count() == 1
    assert templates.first().model == 'gemma3-4b'
