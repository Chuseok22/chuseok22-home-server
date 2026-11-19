from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import NoReverseMatch, reverse


class Tool(models.Model):
    """Lab 페이지에 노출되는 개인 유틸 도구."""

    title = models.CharField(max_length=100, verbose_name='이름')
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=300, verbose_name='설명')
    icon = models.CharField(max_length=8, blank=True, default='', verbose_name='아이콘(이모지)')
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


class ConnectProfile(models.Model):
    """Connect 페이지 헤더와 vCard에 쓰는 영문 프로필. Admin에서 단일 레코드만 유지하는 싱글턴이다."""

    english_name = models.CharField(max_length=100, verbose_name='영문 이름')
    title = models.TextField(verbose_name='직함(여러 줄 가능)')
    email = models.EmailField(blank=True, verbose_name='이메일(vCard)')
    # vCard에 그대로 들어가므로 줄바꿈 등 속성 주입이 가능한 문자를 모델 단계에서 막는다.
    phone = models.CharField(
        max_length=30,
        blank=True,
        validators=[RegexValidator(r'^[0-9+\-() ]*\Z', '숫자, +, -, 괄호, 공백만 입력할 수 있습니다.')],
        verbose_name='전화번호(vCard)',
    )
    avatar = models.ImageField(upload_to='site/connect/avatar/', blank=True, verbose_name='프로필 사진')
    business_card = models.ImageField(
        upload_to='site/connect/card/', blank=True, verbose_name='명함 이미지(영문 면, 페이지와 공유 미리보기에 사용)'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시각')

    class Meta:
        db_table = 'site_connect_profile'
        verbose_name = 'Connect 프로필'
        verbose_name_plural = 'Connect 프로필'

    def __str__(self) -> str:
        return self.english_name

    @property
    def initials(self) -> str:
        words = self.english_name.split()
        if not words:
            return ''
        return (words[0][0] + (words[-1][0] if len(words) > 1 else '')).upper()

    @property
    def title_lines(self) -> list[str]:
        stripped_lines = (line.strip() for line in self.title.splitlines())
        return [line for line in stripped_lines if line]


class ConnectLink(models.Model):
    """Connect 페이지에 노출되는 외부 링크 한 줄."""

    class IconStyle(models.TextChoices):
        GITHUB = 'github', 'GitHub'
        LINKEDIN = 'linkedin', 'LinkedIn'
        SITE = 'site', 'Site'
        INSTAGRAM = 'instagram', 'Instagram'

    title = models.CharField(max_length=60, verbose_name='제목')
    subtitle = models.CharField(max_length=100, blank=True, verbose_name='보조 텍스트(핸들 등)')
    url = models.URLField(verbose_name='링크 URL')
    # Simple Icons 슬러그 또는 전체 아이콘 URL. Simple Icons에서 삭제된 브랜드(LinkedIn 등)는 URL을 직접 넣는다.
    icon = models.CharField(max_length=255, blank=True, verbose_name='Simple Icons 슬러그 또는 아이콘 URL')
    icon_style = models.CharField(
        max_length=20,
        choices=IconStyle.choices,
        default=IconStyle.GITHUB,
        verbose_name='아이콘 배경 스타일',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    is_active = models.BooleanField(default=True, verbose_name='노출')

    class Meta:
        db_table = 'site_connect_link'
        ordering = ['order', 'id']
        verbose_name = 'Connect 링크'
        verbose_name_plural = 'Connect 링크 목록'

    def __str__(self) -> str:
        return self.title
