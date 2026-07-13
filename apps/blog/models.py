from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class Category(models.Model):
    """블로그 카테고리. 대분류(parent=None)/소분류(parent=대분류) 2단계까지만 허용한다."""

    name = models.CharField(max_length=50, unique=True, verbose_name='이름')
    slug = models.SlugField(unique=True, blank=True, verbose_name='슬러그')
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
        # 자기 자신을 부모로 지정하는 자기참조를 막는다.
        if self.parent_id is not None and self.pk is not None and self.parent_id == self.pk:
            raise ValidationError('카테고리는 자기 자신을 상위 카테고리로 지정할 수 없습니다.')
        # 소분류를 다시 누군가의 부모로 지정하는 3단계 이상 중첩을 막는다.
        if self.parent_id and self.parent.parent_id is not None:
            raise ValidationError('카테고리는 2단계(대분류/소분류)까지만 허용됩니다.')

    def save(self, *args: object, **kwargs: object) -> None:
        # Admin 폼 밖(서비스 레이어의 get_or_create 등)에서도 계층 불변조건이 지켜지도록
        # 저장 시점에 항상 clean()을 실행한다. full_clean()이 아닌 clean()만 호출하는 이유는
        # 계층 깊이 검증(parent 관련)만 필요하고, 필드 단위 검증(validate_unique 등)은
        # DB의 unique 제약으로 이미 보장되기 때문이다.
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    """블로그 태그. 대소문자만 다른 동일 태그의 중복 생성을 막는다."""

    name = models.CharField(max_length=50, verbose_name='이름')
    slug = models.SlugField(unique=True, blank=True, verbose_name='슬러그')

    class Meta:
        db_table = 'blog_tag'
        ordering = ['name']
        verbose_name = '태그'
        verbose_name_plural = '태그 목록'
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_tag_name_ci'),
        ]

    def clean(self) -> None:
        # DB의 UniqueConstraint(Lower('name'))는 항상 걸리지만, 어드민 "새 태그 추가" 팝업처럼
        # 폼 검증을 거치는 경로에서 IntegrityError 대신 친절한 메시지를 보여주기 위해
        # 동일 조건을 애플리케이션 레벨에서도 검사한다.
        if Tag.objects.filter(name__iexact=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(f"태그 '{self.name}'이 이미 존재합니다 (대소문자 무시).")

    def save(self, *args: object, **kwargs: object) -> None:
        # slug 자동 생성은 어드민(TagAdmin.save_model)·서비스(get_or_create_tags) 등
        # 호출 시점에 명시적으로 처리한다 — Category/Post와 동일한 패턴.
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    """블로그 포스트. 본문은 Markdown 원문으로 저장한다."""

    title = models.CharField(max_length=200, verbose_name='제목')
    slug = models.SlugField(unique=True, blank=True, verbose_name='슬러그')
    summary = models.CharField(max_length=300, blank=True, verbose_name='요약')
    content = models.TextField(verbose_name='본문 (Markdown)')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name='태그')
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, related_name='posts',
        verbose_name='카테고리',
    )
    repo_url = models.URLField(blank=True, default='', verbose_name='저장소 링크')
    is_published = models.BooleanField(default=False, verbose_name='공개 여부')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='발행일시')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0, verbose_name='조회수')

    class Meta:
        db_table = 'blog_post'
        ordering = ['-published_at']
        verbose_name = '블로그 포스트'
        verbose_name_plural = '블로그 포스트 목록'

    def __str__(self) -> str:
        return self.title
