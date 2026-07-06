from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.blog.models import Post
from apps.blog.services.markdown_renderer import render_markdown


class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = '__all__'

    # Post.tags는 blank=True라 필드는 이미 required=False지만,
    # 빈 값 제출 시 None이 되어 NOT NULL 컬럼에서 IntegrityError가 발생한다.
    def clean_tags(self) -> list:
        return self.cleaned_data.get('tags') or []


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'is_published', 'published_at', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('content_preview',)
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'summary', 'tags', 'is_published', 'published_at')}),
        ('본문', {'fields': ('content', 'content_preview')}),
    )

    @admin.display(description='렌더링 미리보기')
    def content_preview(self, obj: Post) -> str:
        if not obj.content:
            return '-'
        # apps/site 공개 페이지(templates/site/blog_detail.html의 {{ content_html|safe }})와
        # 동일하게, render_markdown()이 이미 bleach로 sanitize한 결과를 신뢰해 그대로 렌더링한다.
        return format_html('<div>{}</div>', mark_safe(render_markdown(obj.content)))
