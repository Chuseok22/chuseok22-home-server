from django.core.exceptions import ValidationError
from django.db import models

from apps.core.icons import is_valid_icon_slug


class Profile(models.Model):
    """포트폴리오 프로필. Admin에서 단일 레코드만 유지하는 싱글턴으로 관리한다."""

    name = models.CharField(max_length=50, verbose_name='이름')
    tagline = models.CharField(max_length=200, verbose_name='한 줄 소개')
    avatar = models.ImageField(upload_to='profile/avatar/', blank=True, verbose_name='프로필 사진')
    bio = models.TextField(blank=True, verbose_name='상세 소개(마크다운)')
    email = models.EmailField(blank=True, verbose_name='이메일')
    github_url = models.URLField(blank=True, verbose_name='GitHub 링크')
    blog_url = models.URLField(blank=True, verbose_name='블로그/홈페이지 링크')
    linkedin_url = models.URLField(blank=True, verbose_name='LinkedIn 링크')
    contribution_graph_url = models.URLField(blank=True, verbose_name='3D 컨트리뷰션 그래프 이미지 URL')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시각')

    class Meta:
        verbose_name = '프로필'
        verbose_name_plural = '프로필'

    def __str__(self) -> str:
        return self.name


class VisitorCounter(models.Model):
    """홈 화면 누적 방문자 수 (싱글턴, pk=1)."""

    count = models.PositiveIntegerField(default=0, verbose_name='누적 방문 수')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='갱신 시각')

    class Meta:
        verbose_name = '방문자 카운터'
        verbose_name_plural = '방문자 카운터'

    def __str__(self) -> str:
        return f'누적 방문 {self.count}회'


class Skill(models.Model):
    """기술스택 항목. 카테고리별로 그룹핑해 홈 화면에 노출한다."""

    class Category(models.TextChoices):
        BACKEND = 'backend', 'Backend'
        FRONTEND = 'frontend', 'Frontend'
        DATABASE = 'database', 'Database'
        INFRA = 'infra', 'Infra'
        TOOL = 'tool', 'Tool'
        ETC = 'etc', 'ETC'

    category = models.CharField(max_length=20, choices=Category.choices, verbose_name='분류')
    name = models.CharField(max_length=50, verbose_name='이름')
    # 벤더링된 Simple Icons 또는 other-brands 세트에 실제로 존재하는 슬러그만 저장 가능하다
    # (icon_slug가 바뀌는 시점에 Skill.clean()에서 검증). CDN 전체 URL은 더 이상 허용하지 않는다.
    icon_slug = models.CharField(max_length=255, blank=True, verbose_name='아이콘 슬러그(벤더링된 세트 기준)')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '기술스택'
        verbose_name_plural = '기술스택 목록'
        ordering = ('category', 'order')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # clean()에서 icon_slug가 "실제로 바뀌었는지"를 판단하기 위한 스냅샷. 이 값이 없으면
        # icon_slug를 건드리지 않는 수정(예: Admin list_editable의 order 일괄 편집)까지
        # full_clean()이 검증해버려서, 검증 도입 이전에 저장된 레거시 데이터가 있는 레코드는
        # 그 어떤 필드도 수정할 수 없게 막혀버린다. 이 게이트는 save()가 아니라 clean()에
        # 둔다 — Django Admin의 list_editable ModelForm은 save()를 거치지 않고
        # BaseModelForm._post_clean()에서 instance.full_clean()을 직접 호출하므로,
        # save()에서만 게이트하면 그 경로에서는 여전히 clean()이 무조건 실행돼 레거시
        # 잘못된 슬러그에 대해 ValidationError가 발생하고, order만 있는 폼에는 icon_slug
        # 필드가 없어 ValueError로 이어진다.
        self._original_icon_slug = self.icon_slug

    def __str__(self) -> str:
        return f'[{self.get_category_display()}] {self.name}'

    def clean(self) -> None:
        super().clean()
        icon_slug_changed = self.pk is None or self.icon_slug != self._original_icon_slug
        if icon_slug_changed and self.icon_slug and not is_valid_icon_slug(self.icon_slug):
            raise ValidationError({
                'icon_slug': (
                    '벤더링된 아이콘 세트(Simple Icons 또는 other-brands)에 없는 슬러그입니다. '
                    'https://simpleicons.org 에서 슬러그를 확인하거나, 없는 브랜드라면 '
                    'apps/core/static/core/icons/other-brands/README.md 절차를 따르세요.'
                )
            })

    def save(self, *args, **kwargs) -> None:
        # 알려진 한계: (1) pk를 직접 지정해 생성하는 경우(Skill(pk=..., icon_slug=...))는
        # self.pk가 이미 채워져 있고 스냅샷도 같은 값이라 검증을 건너뛴다 — 이 프로젝트 코드
        # 어디에서도 pk를 직접 지정해 Skill을 생성하지 않으므로 실질적 위험은 없다.
        # (2) QuerySet.update()/bulk_update()는 save()를 거치지 않아 이 검증이 아예 걸리지 않는다
        # — 이 프로젝트는 Skill에 대해 이 두 메서드를 쓰지 않는다. 둘 다 쓰게 되면 이 시점에
        # 검증 전략을 다시 검토해야 한다.
        self.full_clean()
        super().save(*args, **kwargs)
        self._original_icon_slug = self.icon_slug


class Career(models.Model):
    """이력(직장/학력/수상) 타임라인 항목."""

    class Category(models.TextChoices):
        WORK = 'work', '직장'
        EDUCATION = 'education', '학력'
        AWARD = 'award', '수상'

    category = models.CharField(max_length=20, choices=Category.choices, verbose_name='분류')
    organization = models.CharField(max_length=100, verbose_name='기관명')
    role = models.CharField(max_length=100, verbose_name='역할/직책/학위')
    period_start = models.DateField(verbose_name='시작일')
    period_end = models.DateField(null=True, blank=True, verbose_name='종료일(재직/재학 중이면 비움)')
    description = models.TextField(blank=True, verbose_name='설명')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '이력'
        verbose_name_plural = '이력 목록'
        ordering = ('order',)

    def __str__(self) -> str:
        return f'[{self.get_category_display()}] {self.organization} — {self.role}'


class Activity(models.Model):
    """대외활동(동아리, 커뮤니티 등) 카드."""

    name = models.CharField(max_length=100, verbose_name='활동명')
    description = models.TextField(blank=True, verbose_name='설명')
    period = models.CharField(max_length=100, blank=True, verbose_name='기간')
    link = models.URLField(blank=True, verbose_name='관련 링크')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '활동'
        verbose_name_plural = '활동 목록'
        ordering = ('order',)

    def __str__(self) -> str:
        return self.name


class Certification(models.Model):
    """자격증. 카드에는 자격증명·취득일·발급기관을, 클릭 시 배지 이미지를 확대해 보여준다."""

    name = models.CharField(max_length=100, verbose_name='자격증명')
    issuer = models.CharField(max_length=100, verbose_name='발급기관')
    acquired_date = models.DateField(verbose_name='취득일')
    badge_image = models.ImageField(upload_to='profile/certification/', blank=True, verbose_name='배지 이미지')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '자격증'
        verbose_name_plural = '자격증 목록'
        ordering = ('order',)

    def __str__(self) -> str:
        return f'{self.name} ({self.issuer})'


class PullRequestHighlight(models.Model):
    """포트폴리오용 대표 PR (기간 제한 없이 큐레이션, GithubActivity 캐시와 무관)."""

    title = models.CharField(max_length=200, verbose_name='제목')
    repo_name = models.CharField(max_length=200, verbose_name='저장소 이름')
    pr_url = models.URLField(verbose_name='PR 링크')
    description = models.TextField(blank=True, verbose_name='설명')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '대표 PR'
        verbose_name_plural = '대표 PR 목록'
        ordering = ('order',)

    def __str__(self) -> str:
        return f'[{self.repo_name}] {self.title}'
