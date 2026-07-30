from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.ai.models import PromptTemplate


class TestPromptTemplateExclusiveActivation(TestCase):
    def test_같은_feature에서_새_활성_프롬프트_저장시_기존_활성_프롬프트가_비활성화된다(self) -> None:
        first = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='v1',
            system_prompt='첫 번째 프롬프트',
            model='functiongemma',
            is_active=True,
        )

        second = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='v2',
            system_prompt='두 번째 프롬프트',
            model='functiongemma',
            is_active=True,
        )

        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)

    def test_다른_feature의_활성_프롬프트는_영향받지_않는다(self) -> None:
        chatbot_template = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='챗봇용',
            system_prompt='챗봇 프롬프트',
            model='functiongemma',
            is_active=True,
        )

        PromptTemplate.objects.create(
            feature='other_feature',
            name='다른 기능용',
            system_prompt='다른 프롬프트',
            model='functiongemma',
            is_active=True,
        )

        chatbot_template.refresh_from_db()
        self.assertTrue(chatbot_template.is_active)

    def test_is_active_false로_저장하면_다른_레코드에_영향없다(self) -> None:
        active = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='활성',
            system_prompt='프롬프트',
            model='functiongemma',
            is_active=True,
        )

        PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='비활성 초안',
            system_prompt='초안',
            model='functiongemma',
            is_active=False,
        )

        active.refresh_from_db()
        self.assertTrue(active.is_active)

    def test_save를_우회해_같은_feature에_활성_레코드_두_개를_만들면_DB_제약이_거부한다(self) -> None:
        # bulk_create/queryset.update()처럼 save()를 거치지 않는 경로는 애플리케이션 레벨의
        # 배타적 활성화 로직을 우회할 수 있으므로, DB 레벨 UniqueConstraint가 실제로
        # 두 번째 활성 레코드 생성을 막는지 검증한다.
        first = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='v1',
            system_prompt='첫 번째 프롬프트',
            model='functiongemma',
            is_active=True,
        )
        second = PromptTemplate.objects.create(
            feature=PromptTemplate.Feature.CHATBOT,
            name='v2',
            system_prompt='두 번째 프롬프트',
            model='functiongemma',
            is_active=False,
        )
        self.assertTrue(PromptTemplate.objects.get(pk=first.pk).is_active)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PromptTemplate.objects.filter(pk=second.pk).update(is_active=True)
