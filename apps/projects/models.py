from django.db import models


class ProjectCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'projects_project_category'
        ordering = ['order']

    def __str__(self) -> str:
        return self.name


class ProjectStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'projects_project_status'
        ordering = ['order']

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    category = models.ForeignKey(ProjectCategory, on_delete=models.PROTECT, related_name='projects')
    title = models.CharField(max_length=100)
    description = models.TextField()
    tags = models.JSONField(default=list)
    status = models.ForeignKey(ProjectStatus, on_delete=models.PROTECT, related_name='projects')
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
        ordering = ['category__order', 'order', '-created_at']

    def __str__(self) -> str:
        return f'[{self.category.name}] {self.title}'
