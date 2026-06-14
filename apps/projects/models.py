from django.db import models


class ProjectCategory(models.TextChoices):
    TEAM = 'team', '팀 프로젝트'
    SIDE = 'side', '사이드 프로젝트'
    OPEN_SOURCE = 'open_source', '오픈소스'


class ProjectStatus(models.TextChoices):
    IN_PROGRESS = 'in_progress', '진행중'
    COMPLETED = 'completed', '완료'
    ARCHIVED = 'archived', '중단'


class Project(models.Model):
    category = models.CharField(
        max_length=20,
        choices=ProjectCategory.choices,
        db_index=True,
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    tags = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=ProjectStatus.choices)
    order = models.PositiveIntegerField(default=0)

    period = models.CharField(max_length=50, blank=True)
    team_size = models.PositiveSmallIntegerField(null=True, blank=True)
    role = models.CharField(max_length=100, blank=True)
    highlights = models.JSONField(default=list, blank=True)
    github_href = models.URLField(blank=True)
    demo_href = models.URLField(blank=True)
    title_href = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects_project'
        ordering = ['category', 'order', '-created_at']

    def __str__(self) -> str:
        return f'[{self.get_category_display()}] {self.title}'
