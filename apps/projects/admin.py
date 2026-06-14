from django.contrib import admin

from apps.projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'order', 'updated_at')
    list_filter = ('category', 'status')
    ordering = ('category', 'order')
    search_fields = ('title', 'description')
    list_editable = ('order',)

    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'title', 'description', 'tags', 'status', 'order'),
        }),
        ('상세 정보', {
            'fields': ('period', 'team_size', 'role', 'highlights'),
            'classes': ('collapse',),
        }),
        ('링크', {
            'fields': ('github_href', 'demo_href', 'title_href'),
        }),
    )
