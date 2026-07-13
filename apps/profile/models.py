from django.db import models


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
    # Simple Icons 슬러그(짧은 문자열) 또는 다른 아이콘 CDN의 전체 URL(Simple Icons에 없는
    # 브랜드용) 둘 다 저장할 수 있어야 해서 URL 길이를 감안해 넉넉히 잡는다.
    icon_slug = models.CharField(max_length=255, blank=True, verbose_name='Simple Icons 슬러그 또는 아이콘 URL')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')

    class Meta:
        verbose_name = '기술스택'
        verbose_name_plural = '기술스택 목록'
        ordering = ('category', 'order')

    def __str__(self) -> str:
        return f'[{self.get_category_display()}] {self.name}'


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
    """자격증. 카드에는 이름/배지만, 클릭 시 상세 정보를 모달로 보여준다."""

    name = models.CharField(max_length=100, verbose_name='자격증명')
    issuer = models.CharField(max_length=100, verbose_name='발급기관')
    acquired_date = models.DateField(verbose_name='취득일')
    credential_number = models.CharField(max_length=100, blank=True, verbose_name='자격증 번호')
    credential_url = models.URLField(blank=True, verbose_name='커리큘럼/검증 링크')
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
