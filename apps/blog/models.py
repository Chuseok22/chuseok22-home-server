from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    """블로그 카테고리. 대분류(parent=None)/소분류(parent=대분류) 2단계까지만 허용한다."""

    name = models.CharField(max_length=50, unique=True, verbose_name='이름')
    slug = models.SlugField(unique=True, verbose_name='슬러그')
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.PROTECT, related_name='children',
        verbose_name='상위 카테고리',
    )

    class Meta:
        db_table = 'blog_category'
        ordering = ['name']
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리 목록'

    def clean(self) -> None:
        # 소분류를 다시 누군가의 부모로 지정하는 3단계 이상 중첩을 막는다.
        if self.parent_id and self.parent.parent_id is not None:
            raise ValidationError('카테고리는 2단계(대분류/소분류)까지만 허용됩니다.')

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    """블로그 포스트. 본문은 Markdown 원문으로 저장한다."""

    title = models.CharField(max_length=200, verbose_name='제목')
    slug = models.SlugField(unique=True, verbose_name='슬러그')
    summary = models.CharField(max_length=300, blank=True, verbose_name='요약')
    content = models.TextField(verbose_name='본문 (Markdown)')
    tags = models.JSONField(default=list, blank=True, verbose_name='태그')
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, related_name='posts',
        verbose_name='카테고리',
    )
    repo_url = models.URLField(blank=True, verbose_name='저장소 링크')
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
