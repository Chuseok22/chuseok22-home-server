from django.db import models


class Tool(models.Model):
    """Lab 페이지에 노출되는 개인 유틸 도구."""

    title = models.CharField(max_length=100, verbose_name='이름')
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=300, verbose_name='설명')
    is_owner_only = models.BooleanField(default=False, verbose_name='소유자 전용')
    url_name = models.CharField(max_length=100, verbose_name='연결할 URL name')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'site_tool'
        ordering = ['order', 'title']
        verbose_name = 'Lab 도구'
        verbose_name_plural = 'Lab 도구 목록'

    def __str__(self) -> str:
        return self.title
