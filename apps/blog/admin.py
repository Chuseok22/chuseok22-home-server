from django import forms
from django.contrib import admin
from django.db.models import ForeignKey
from django.http import HttpRequest, JsonResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.blog.models import Category, Post
from apps.blog.services.markdown_renderer import render_markdown
from apps.blog.services.media_storage import save_uploaded_media
from apps.blog.services.slug import generate_unique_slug


class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = '__all__'

    # Post.tags는 blank=True라 필드는 이미 required=False지만,
    # 빈 값 제출 시 None이 되어 NOT NULL 컬럼에서 IntegrityError가 발생한다.
    def clean_tags(self) -> list:
        return self.cleaned_data.get('tags') or []


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    prepopulated_fields = {'slug': ('name',)}

    def save_model(self, request: HttpRequest, obj: Category, form: forms.ModelForm, change: bool) -> None:
        if not obj.slug:
            obj.slug = generate_unique_slug(Category, obj.name)
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field: ForeignKey, request: HttpRequest, **kwargs) -> forms.Field:
        # 소분류가 다른 소분류의 부모가 되는 3단계 중첩을 UI 단에서부터 차단한다.
        if db_field.name == 'parent':
            queryset = Category.objects.filter(parent__isnull=True)
            # 최상위 카테고리 편집 시 자기 자신을 부모로 선택하는 자기참조를 막는다.
            object_id = request.resolver_match.kwargs.get('object_id') if request.resolver_match else None
            if object_id:
                queryset = queryset.exclude(pk=object_id)
            kwargs['queryset'] = queryset
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'is_published', 'published_at', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('content_preview',)
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'summary', 'category', 'repo_url', 'tags', 'is_published', 'published_at')}),
        ('본문', {'fields': ('content', 'content_preview')}),
    )

    def save_model(self, request: HttpRequest, obj: Post, form: forms.ModelForm, change: bool) -> None:
        if not obj.slug:
            obj.slug = generate_unique_slug(Post, obj.title)
        super().save_model(request, obj, form, change)

    class Media:
        js = ('blog/admin/post_media_upload.js',)

    def get_urls(self) -> list:
        custom_urls = [
            path(
                'upload-media/',
                self.admin_site.admin_view(self.upload_media_view),
                name='blog_post_upload_media',
            ),
        ]
        return custom_urls + super().get_urls()

    def upload_media_view(self, request: HttpRequest) -> JsonResponse:
        # admin_view()는 로그인·staff 여부만 검사하므로, Post 변경 권한이 없는 staff 계정의
        # 업로드를 막으려면 모델 단위 권한을 별도로 확인해야 한다.
        if not self.has_change_permission(request):
            return JsonResponse({'success': False, 'error_message': '권한이 없습니다.'}, status=403)

        if request.method != 'POST' or 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error_message': '업로드할 파일이 없습니다.'}, status=400)

        result = save_uploaded_media(request.FILES['file'])
        if not result.success:
            return JsonResponse({'success': False, 'error_message': result.error_message}, status=400)

        return JsonResponse({'success': True, 'url': result.url, 'markdown': result.markdown})

    @admin.display(description='렌더링 미리보기')
    def content_preview(self, obj: Post) -> str:
        if not obj.content:
            return '-'
        # apps/site 공개 페이지(templates/site/blog_detail.html의 {{ content_html|safe }})와
        # 동일하게, render_markdown()이 이미 bleach로 sanitize한 결과를 신뢰해 그대로 렌더링한다.
        return format_html('<div>{}</div>', mark_safe(render_markdown(obj.content)))
