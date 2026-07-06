from django import forms

from apps.blog.models import Post
from apps.projects.models import Project


class ProjectForm(forms.ModelForm):
    # Project.tags는 blank=True가 없어 ModelForm이 필수 필드로 변환하는데,
    # Django JSONField는 빈 리스트([])도 empty_values로 취급해 "필수" 검증에 걸린다.
    # required=False로 완화하고, 필드 생략 시 None이 아닌 빈 리스트로 저장되도록 정규화한다
    # (모델 컬럼이 NOT NULL이라 None을 그대로 저장하면 IntegrityError 발생).
    tags = forms.JSONField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': 'textarea textarea-bordered', 'placeholder': '["Django", "PostgreSQL"]'}))

    class Meta:
        model = Project
        fields = [
            'category', 'title', 'description', 'tags', 'status', 'order',
            'period', 'team_size', 'role', 'highlights',
            'github_href', 'demo_href', 'title_href',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'textarea textarea-bordered'}),
            'highlights': forms.Textarea(attrs={'rows': 3, 'class': 'textarea textarea-bordered', 'placeholder': '["핵심 성과 1", "핵심 성과 2"]'}),
        }

    def clean_tags(self) -> list:
        return self.cleaned_data.get('tags') or []

    # Project.highlights도 blank=True라 폼 필드는 이미 required=False로 생성되지만,
    # 빈 텍스트영역 제출 시 JSONField.to_python('')가 None을 반환해 NOT NULL 컬럼에서
    # IntegrityError가 발생한다. tags와 동일하게 None을 빈 리스트로 정규화한다.
    def clean_highlights(self) -> list:
        return self.cleaned_data.get('highlights') or []


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'summary', 'content', 'tags', 'is_published', 'published_at']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 12, 'class': 'textarea textarea-bordered w-full'}),
            'tags': forms.Textarea(attrs={'rows': 2, 'class': 'textarea textarea-bordered', 'placeholder': '["Django", "블로그"]'}),
        }

    # Post.tags는 blank=True라 폼 필드가 이미 required=False로 생성되지만,
    # 빈 텍스트영역 제출 시 cleaned_data['tags']가 None이 되어 NOT NULL 컬럼에서
    # IntegrityError가 발생한다. ProjectForm.clean_tags와 동일한 정규화를 적용한다.
    def clean_tags(self) -> list:
        return self.cleaned_data.get('tags') or []


class ScheduledJobConfigForm(forms.Form):
    is_enabled = forms.BooleanField(required=False)
    cron_hour = forms.IntegerField(min_value=0, max_value=23)
    cron_minute = forms.IntegerField(min_value=0, max_value=59)
