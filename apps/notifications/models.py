from django.db import models


class NoticeSource(models.Model):
    """공지사항 크롤링 대상 사이트 정보"""
    name = models.CharField(max_length=100, verbose_name='사이트명')
    url = models.URLField(verbose_name='목록 URL')
    # 크롤러 타입 식별자 — 새 사이트 추가 시 crawlers/ 에 구현체 등록 후 사용
    crawler_type = models.CharField(max_length=50, verbose_name='크롤러 타입')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '공지 출처'
        verbose_name_plural = '공지 출처 목록'

    def __str__(self) -> str:
        return self.name


class Notice(models.Model):
    """크롤링된 공지사항 항목 및 알림 발송 이력"""
    source = models.ForeignKey(
        NoticeSource,
        on_delete=models.CASCADE,
        related_name='notices',
        verbose_name='출처',
    )
    article_id = models.CharField(max_length=100, verbose_name='원본 글 ID')
    title = models.CharField(max_length=500, verbose_name='제목')
    url = models.URLField(verbose_name='상세 URL')
    published_at = models.DateField(null=True, blank=True, verbose_name='게시일')
    is_notified = models.BooleanField(default=False, verbose_name='알림 발송 여부')
    notified_at = models.DateTimeField(null=True, blank=True, verbose_name='알림 발송 시각')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '공지사항'
        verbose_name_plural = '공지사항 목록'
        unique_together = ('source', 'article_id')

    def __str__(self) -> str:
        return f'[{self.source.name}] {self.title}'
