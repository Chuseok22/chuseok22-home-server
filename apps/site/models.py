from django.core.exceptions import ValidationError
from django.db import models
from django.urls import NoReverseMatch, reverse


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

    def clean(self) -> None:
        # url_name이 reverse 불가능한 값이면 lab_index 공개 페이지가 NoReverseMatch로 깨지므로 저장 전 검증한다.
        try:
            reverse(self.url_name)
        except NoReverseMatch as error:
            raise ValidationError({'url_name': 'reverse할 수 없는 URL name입니다.'}) from error
