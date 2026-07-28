import re
from typing import Any

from django import forms
from django.contrib import admin
from django.core.validators import URLValidator

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


class ExtraLinksField(forms.Field):
    """"라벨|URL" 형식의 줄바꿈 텍스트를 [{"label": str, "url": str}, ...] 리스트로 변환하는 폼 필드.

    GitHub/iOS/Android/웹사이트처럼 고정 아이콘이 있는 링크와 달리, 노션·발표자료 등 라벨이
    프로젝트마다 제각각인 부가 링크를 라벨과 함께 임의 개수 저장하기 위해 사용한다.
    """

    widget = forms.Textarea

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return '\n'.join(f'{item["label"]}|{item["url"]}' for item in value)
        return value

    def to_python(self, value: str | None) -> list[dict[str, str]]:
        if not value:
            return []

        url_validator = URLValidator()
        links: list[dict[str, str]] = []
        for line_number, line in enumerate(value.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if '|' not in stripped:
                raise forms.ValidationError(f'{line_number}번째 줄: "라벨|URL" 형식이 아닙니다.')
            label, url = stripped.split('|', 1)
            label, url = label.strip(), url.strip()
            if not label:
                raise forms.ValidationError(f'{line_number}번째 줄: 라벨이 비어 있습니다.')
            try:
                url_validator(url)
            except forms.ValidationError as err:
                raise forms.ValidationError(f'{line_number}번째 줄: 유효한 URL이 아닙니다.') from err
            links.append({'label': label, 'url': url})
        return links


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
    # tags/highlights는 JSONField(문자열 리스트)지만, Admin 기본 JSONField 위젯은
    # 순수 JSON 문법을 요구해 입력이 번거롭다. NewlineSeparatedListField로 교체해
    # 한 줄에 항목 하나씩 입력할 수 있게 한다.
    # Project.tags는 모델에 blank=True가 없어 기본 폼이 필수 필드로 만들지만,
    # 빈 리스트([])도 저장 가능해야 하므로 required=False로 완화한다.
    tags = NewlineSeparatedListField(
        required=False,
        help_text='한 줄에 태그 하나씩 입력하세요. 예: Java',
    )
    highlights = NewlineSeparatedListField(
        required=False,
        help_text='한 줄에 항목 하나씩 입력하세요. 앞의 불릿 기호(•, -, *)는 자동으로 제거됩니다.',
    )
    extra_links = ExtraLinksField(
        required=False,
        help_text='한 줄에 "라벨|URL" 형식으로 입력하세요. 예: Notion|https://notion.so/xxx',
    )

    class Meta:
        model = Project
        fields = '__all__'


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
            'fields': ('github_href', 'web_site_href', 'ios_href', 'android_href', 'title_href', 'extra_links'),
        }),
    )
