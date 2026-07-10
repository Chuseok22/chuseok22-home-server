from django.db import models


class GithubActivity(models.Model):
    """GitHub Public Events API로 수집한 활동 이력 (DB 캐싱)"""
    # GitHub 이벤트 ID — 수집 중복 방지 키
    event_id = models.CharField(max_length=50, unique=True, verbose_name='이벤트 ID')
    event_type = models.CharField(max_length=50, verbose_name='이벤트 유형')
    repo_name = models.CharField(max_length=200, verbose_name='저장소 이름')
    title = models.CharField(max_length=200, verbose_name='표시 제목')
    meta = models.CharField(max_length=500, verbose_name='표시 설명')
    occurred_at = models.DateTimeField(db_index=True, verbose_name='이벤트 발생 시각')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='DB 수집 시각')

    class Meta:
        verbose_name = 'GitHub 활동'
        verbose_name_plural = 'GitHub 활동 목록'
        ordering = ('-occurred_at',)

    def __str__(self) -> str:
        return f'[{self.event_type}] {self.repo_name}'


class GithubContributionDay(models.Model):
    """GitHub GraphQL API로 수집한 날짜별 컨트리뷰션(잔디) 수"""
    date = models.DateField(unique=True, verbose_name='날짜')
    contribution_count = models.PositiveIntegerField(default=0, verbose_name='컨트리뷰션 수')

    class Meta:
        verbose_name = 'GitHub 컨트리뷰션'
        verbose_name_plural = 'GitHub 컨트리뷰션 목록'
        ordering = ('date',)

    def __str__(self) -> str:
        return f'{self.date} ({self.contribution_count})'


class GithubProfileStats(models.Model):
    """GitHub 프로필 요약 통계 (싱글턴 레코드, pk=1 고정)"""
    total_stars = models.PositiveIntegerField(default=0, verbose_name='총 star 수')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='갱신 시각')

    class Meta:
        verbose_name = 'GitHub 프로필 통계'
        verbose_name_plural = 'GitHub 프로필 통계'

    def __str__(self) -> str:
        return f'star {self.total_stars}개 (갱신: {self.updated_at:%Y-%m-%d})'
