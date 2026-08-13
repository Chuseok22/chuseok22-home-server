from django.core.exceptions import ValidationError
from django.db import models


class CertificationDefinition(models.Model):
    """자격증 마스터 데이터 — 관리자가 등록한 자체가 '추적 대상'이다."""

    class Category(models.TextChoices):
        NATIONAL_TECH = 'national_tech', '국가기술자격'
        IT_PRIVATE = 'it_private', 'IT 민간자격'
        LANGUAGE = 'language', '어학'
        ETC = 'etc', '기타'

    name = models.CharField(max_length=100, verbose_name='자격증명')
    issuer = models.CharField(max_length=100, verbose_name='발급기관')
    category = models.CharField(max_length=20, choices=Category.choices, verbose_name='분류')
    official_url = models.URLField(blank=True, default='', verbose_name='공식 사이트')
    # crawlers/registry.py의 CRAWLER_REGISTRY 키('hrdkorea_api', 'manual' 등)
    crawler_type = models.CharField(max_length=30, verbose_name='크롤러 타입')
    # hrdkorea_api 크롤러의 종목코드(jmCd) 등 크롤러별 소스 식별자
    crawler_source_id = models.CharField(max_length=100, blank=True, default='', verbose_name='크롤러 소스 식별자')
    # CCNA(Pearson VUE 예약제)처럼 고정 회차 없이 상시 응시 가능한 자격증. True면 ExamSchedule을
    # 두지 않고 캘린더/타임라인에서 제외하며, "추적 중인 자격증" 목록에 "상시 접수" 배지로만 노출한다.
    is_always_open = models.BooleanField(default=False, verbose_name='상시 접수 여부')
    is_active = models.BooleanField(default=True, verbose_name='추적 활성화')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '자격증'
        verbose_name_plural = '자격증 목록'
        ordering = ('order', 'name')

    def __str__(self) -> str:
        return self.name


class ExamSchedule(models.Model):
    """회차별 시험 일정 1건."""

    certification = models.ForeignKey(
        CertificationDefinition, related_name='schedules', on_delete=models.CASCADE, verbose_name='자격증',
    )
    round_name = models.CharField(max_length=50, verbose_name='회차명')
    registration_start = models.DateField(verbose_name='원서접수 시작일')
    registration_end = models.DateField(verbose_name='원서접수 마감일')
    exam_date = models.DateField(null=True, blank=True, verbose_name='시험일')
    result_announcement_date = models.DateField(null=True, blank=True, verbose_name='합격자 발표일')
    source_url = models.URLField(blank=True, default='', verbose_name='출처 링크')
    registration_open_notified = models.BooleanField(default=False, verbose_name='접수 시작 알림 발송 여부')
    registration_deadline_notified = models.BooleanField(default=False, verbose_name='접수 마감 임박 알림 발송 여부')

    class Meta:
        verbose_name = '시험 일정'
        verbose_name_plural = '시험 일정 목록'
        ordering = ('registration_start',)
        constraints = [
            models.UniqueConstraint(fields=('certification', 'round_name'), name='unique_certification_round'),
            models.CheckConstraint(
                condition=models.Q(registration_end__gte=models.F('registration_start')),
                name='exam_schedule_registration_end_gte_start',
            ),
        ]

    def __str__(self) -> str:
        return f'[{self.certification.name}] {self.round_name}'

    def clean(self) -> None:
        # CheckConstraint는 DB 레벨 최종 방어선이고, 이 clean()은 Admin 저장 시(ModelForm이
        # full_clean을 호출) 필드 단위 에러 메시지로 바로 보여주기 위한 것이다.
        if self.registration_end < self.registration_start:
            raise ValidationError({'registration_end': '원서접수 마감일은 시작일보다 빠를 수 없습니다.'})
