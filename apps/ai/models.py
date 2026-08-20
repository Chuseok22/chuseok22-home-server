from django.db import models, transaction
from django.utils import timezone


class PromptTemplate(models.Model):
    """기능(feature)별 AI 프롬프트·모델 설정. 같은 feature 내에서는 항상 하나만 활성화된다."""

    class Feature(models.TextChoices):
        CHATBOT = 'chatbot', '사이트 챗봇'
        GITHUB_TRENDING_SUMMARY = 'github_trending_summary', 'GitHub 트렌딩 요약'
        CLUB_RECRUITMENT_DETECTION = 'club_recruitment_detection', '동아리 모집 여부 판별'
        # 향후 기능 추가 시 choice만 추가하면 되지만, Django 5.1은 choices 변경도 모델 마이그레이션
        # 상태로 추적하므로 makemigrations를 반드시 실행해야 한다 (DB 스키마상 no-op AlterField).

    feature = models.CharField(max_length=50, choices=Feature.choices, verbose_name='기능')
    name = models.CharField(max_length=100, verbose_name='프롬프트 이름')
    system_prompt = models.TextField(verbose_name='시스템 프롬프트')
    model = models.CharField(max_length=100, verbose_name='SUH-AIder 모델명')
    is_active = models.BooleanField(default=False, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시각')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시각')

    class Meta:
        ordering = ('feature', '-updated_at')
        verbose_name = 'AI 프롬프트'
        verbose_name_plural = 'AI 프롬프트 목록'
        constraints = [
            # 애플리케이션 레벨(save())의 배타적 활성화 로직은 bulk_create/queryset.update()
            # 같은 우회 경로에서 보장되지 않으므로, DB 레벨에서도 feature당 활성 레코드가
            # 최대 1개임을 강제한다.
            models.UniqueConstraint(
                fields=['feature'], condition=models.Q(is_active=True),
                name='unique_active_prompt_template_per_feature',
            ),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        # 같은 feature 내에서 활성 프롬프트는 항상 하나만 존재해야 하므로, 새로 활성화되는
        # 레코드를 저장하기 직전에 같은 feature의 기존 활성 레코드를 자동으로 내린다.
        # 비활성화된 레코드는 삭제하지 않으므로 이 테이블 자체가 프롬프트 변경 이력이 된다.
        # 두 단계(기존 레코드 비활성화 + 신규 레코드 저장) 사이에 실패가 발생해도 활성
        # 레코드가 0개로 남지 않도록 원자적으로 처리한다.
        if self.is_active:
            with transaction.atomic():
                # queryset.update()는 save()를 거치지 않아 auto_now=True인 updated_at이
                # 자동 갱신되지 않으므로, 비활성화 시각이 변경 이력에 정확히 남도록 직접 채운다.
                PromptTemplate.objects.filter(
                    feature=self.feature, is_active=True,
                ).exclude(pk=self.pk).update(is_active=False, updated_at=timezone.now())
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'[{self.get_feature_display()}] {self.name} ({"활성" if self.is_active else "비활성"})'
