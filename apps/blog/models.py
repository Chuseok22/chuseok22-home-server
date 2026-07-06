from django.db import models


class Post(models.Model):
    """블로그 포스트. 본문은 Markdown 원문으로 저장한다."""

    title = models.CharField(max_length=200, verbose_name='제목')
    slug = models.SlugField(unique=True, verbose_name='슬러그')
    summary = models.CharField(max_length=300, blank=True, verbose_name='요약')
    content = models.TextField(verbose_name='본문 (Markdown)')
    tags = models.JSONField(default=list, blank=True, verbose_name='태그')
    is_published = models.BooleanField(default=False, verbose_name='공개 여부')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='발행일시')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'blog_post'
        ordering = ['-published_at']
        verbose_name = '블로그 포스트'
        verbose_name_plural = '블로그 포스트 목록'

    def __str__(self) -> str:
        return self.title
