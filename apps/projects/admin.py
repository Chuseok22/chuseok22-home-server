import re
from typing import Any

from django import forms
from django.contrib import admin

from apps.projects.models import Project, ProjectCategory, ProjectStatus


# '•'는 뒤에 공백이 없어도 불릿으로 간주하지만, '-'/'*'는 뒤에 공백이 있을 때만
# 불릿으로 취급한다. 공백 없이 붙으면 '-Xmx512m', '*args'처럼 값 자체의 일부일
# 수 있어 내용을 훼손하지 않기 위함이다.
_BULLET_PREFIX_PATTERN = re.compile(r'^(?:•\s*|[-*]\s+)')


class NewlineSeparatedListField(forms.Field):
    """줄바꿈으로 구분된 일반 텍스트를 문자열 리스트로 변환하는 폼 필드.

    tags/highlights처럼 JSONField에 문자열 리스트를 저장하는 필드에서, Admin 기본
    JSONField 위젯이 요구하는 JSON 문법(대괄호·따옴표·쉼표) 없이 한 줄에 항목
    하나씩 입력할 수 있도록 한다. 각 줄 앞의 흔한 불릿 기호(•, -, *)와 공백은
    자동으로 제거한다.
    """

    widget = forms.Textarea

    def prepare_value(self, value: Any) -> Any:
        # 과거 raw JSON 위젯으로 문자열이 아닌 값(숫자 등)이 저장돼 있을 수 있으므로
        # str()로 변환해 join 중 TypeError가 나지 않도록 한다.
        if isinstance(value, list):
            return '\n'.join(str(item) for item in value)
        return value

    def to_python(self, value: str | None) -> list[str]:
        if not value:
            return []

        items: list[str] = []
        for line in value.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            stripped = _BULLET_PREFIX_PATTERN.sub('', stripped).strip()
            if stripped:
                items.append(stripped)
        return items


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
