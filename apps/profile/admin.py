from django import forms
from django.contrib import admin
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from apps.profile.models import (
    Activity,
    Career,
    Certification,
    Profile,
    PullRequestHighlight,
    Skill,
    VisitorCounter,
)
from apps.profile.services.avatar_crop import CropBox, crop_avatar


class SingletonAdminMixin:
    """이미 레코드가 하나라도 있으면 Admin에서 추가 화면을 차단하는 믹스인 (싱글턴 모델 전용)."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return super().has_add_permission(request) and not self.model.objects.exists()


class ProfileAdminForm(forms.ModelForm):
    # tagline은 홈 화면 헤어로에서 줄바꿈을 지원(linebreaksbr)하므로,
    # 기본 한 줄 입력창(TextInput)이 아닌 여러 줄 입력이 가능한 Textarea로 노출한다.

    # 아바타 크롭 UI(avatar_crop.js)가 기록하는 원본 이미지 픽셀 좌표. 모델 필드가 아니라
    # 폼에서만 쓰고 save()에서 소비한 뒤 버린다.
    avatar_crop_x = forms.IntegerField(required=False, widget=forms.HiddenInput)
    avatar_crop_y = forms.IntegerField(required=False, widget=forms.HiddenInput)
    avatar_crop_width = forms.IntegerField(required=False, widget=forms.HiddenInput)
    avatar_crop_height = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Profile
        fields = '__all__'
        widgets = {
            'tagline': forms.Textarea(attrs={'rows': 3}),
        }

    def save(self, commit: bool = True) -> Profile:
        new_avatar = self.cleaned_data.get('avatar')
        if isinstance(new_avatar, UploadedFile):
            self.instance.avatar = crop_avatar(new_avatar, self._build_crop_box())
        return super().save(commit=commit)

    def _build_crop_box(self) -> CropBox | None:
        x = self.cleaned_data.get('avatar_crop_x')
        y = self.cleaned_data.get('avatar_crop_y')
        width = self.cleaned_data.get('avatar_crop_width')
        height = self.cleaned_data.get('avatar_crop_height')
        if None in (x, y, width, height):
            return None
        return CropBox(x=x, y=y, width=width, height=height)


@admin.register(Profile)
class ProfileAdmin(SingletonAdminMixin, admin.ModelAdmin):
    form = ProfileAdminForm
    list_display = ('name', 'tagline', 'updated_at')
    readonly_fields = ('updated_at',)

    class Media:
        js = ('profile/admin/avatar_crop.js',)


@admin.register(VisitorCounter)
class VisitorCounterAdmin(SingletonAdminMixin, admin.ModelAdmin):
    list_display = ('count', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'order')
    list_filter = ('category',)
    list_editable = ('order',)
    ordering = ('category', 'order')


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ('organization', 'role', 'category', 'period_start', 'period_end', 'order')
    list_filter = ('category',)
    list_editable = ('order',)
    ordering = ('order',)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'period', 'order')
    list_editable = ('order',)
    ordering = ('order',)


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'issuer', 'acquired_date', 'order')
    list_editable = ('order',)
    ordering = ('order',)


@admin.register(PullRequestHighlight)
class PullRequestHighlightAdmin(admin.ModelAdmin):
    list_display = ('title', 'repo_name', 'order')
    list_editable = ('order',)
    ordering = ('order',)
