from django import forms
from django.contrib import admin

from apps.projects.models import Project, ProjectCategory, ProjectStatus


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    ordering = ('order',)


@admin.register(ProjectStatus)
class ProjectStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    ordering = ('order',)


class ProjectAdminForm(forms.ModelForm):
    # Project.tags는 blank=True가 없어 기본 폼이 필수 필드로 만드는데,
    # JSONField는 빈 리스트([])도 필수 검증에 걸리므로 required=False로 완화한다.
    tags = forms.JSONField(required=False)

    class Meta:
        model = Project
        fields = '__all__'

    def clean_tags(self) -> list:
        return self.cleaned_data.get('tags') or []

    # Project.highlights는 blank=True라 필드 자체는 이미 required=False지만,
    # 빈 값 제출 시 JSONField.to_python('')이 None을 반환해 NOT NULL 컬럼에서
    # IntegrityError가 발생한다. None을 빈 리스트로 정규화한다.
    def clean_highlights(self) -> list:
        return self.cleaned_data.get('highlights') or []


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    list_display = ('title', 'category', 'status', 'order', 'updated_at')
    list_filter = ('category', 'status')
    ordering = ('category__order', 'order')
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
