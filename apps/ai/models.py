from django.db import models


class PromptTemplate(models.Model):
    """기능(feature)별 AI 프롬프트·모델 설정. 같은 feature 내에서는 항상 하나만 활성화된다."""

    class Feature(models.TextChoices):
        CHATBOT = 'chatbot', '사이트 챗봇'
        # 향후 기능 추가 시 choice만 추가한다 (choices는 DB 제약이 아니므로 별도 마이그레이션 불필요).

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

    def save(self, *args: object, **kwargs: object) -> None:
        # 같은 feature 내에서 활성 프롬프트는 항상 하나만 존재해야 하므로, 새로 활성화되는
        # 레코드를 저장하기 직전에 같은 feature의 기존 활성 레코드를 자동으로 내린다.
        # 비활성화된 레코드는 삭제하지 않으므로 이 테이블 자체가 프롬프트 변경 이력이 된다.
        if self.is_active:
            PromptTemplate.objects.filter(
                feature=self.feature, is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'[{self.get_feature_display()}] {self.name} ({"활성" if self.is_active else "비활성"})'
