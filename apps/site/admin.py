from django import forms
from django.contrib import admin
from django.core.files.uploadedfile import UploadedFile

from apps.profile.admin import SingletonAdminMixin
from apps.profile.services.avatar_crop import crop_avatar
from apps.site.models import ConnectLink, ConnectProfile, Tool
from apps.site.services.card_image import resize_card_image


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'is_owner_only', 'order')
    list_editable = ('order',)


class ConnectProfileAdminForm(forms.ModelForm):
    class Meta:
        model = ConnectProfile
        fields = '__all__'
        widgets = {
            'title': forms.Textarea(attrs={'rows': 3}),
        }

    def save(self, commit: bool = True) -> ConnectProfile:
        new_avatar = self.cleaned_data.get('avatar')
        if isinstance(new_avatar, UploadedFile):
            # HEIC·대용량 원본이 그대로 서빙되지 않도록 기존 프로필 아바타와 같은 중앙 정사각 크롭을 쓴다.
            self.instance.avatar = crop_avatar(new_avatar, None)
        new_business_card = self.cleaned_data.get('business_card')
        if isinstance(new_business_card, UploadedFile):
            # 공유 미리보기에 쓰는 이미지가 수 MB 원본이나 HEIC로 서빙되지 않게 가로 1200px로 줄인다.
            self.instance.business_card = resize_card_image(new_business_card)
        return super().save(commit=commit)


@admin.register(ConnectProfile)
class ConnectProfileAdmin(SingletonAdminMixin, admin.ModelAdmin):
    form = ConnectProfileAdminForm
    list_display = ('english_name', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(ConnectLink)
class ConnectLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')
