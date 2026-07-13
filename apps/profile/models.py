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
