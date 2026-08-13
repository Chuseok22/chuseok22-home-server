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
