from django.contrib import admin
from django.http import HttpRequest

from apps.profile.models import Profile, VisitorCounter


class SingletonAdminMixin:
    """이미 레코드가 하나라도 있으면 Admin에서 추가 화면을 차단하는 믹스인 (싱글턴 모델 전용)."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not self.model.objects.exists()


@admin.register(Profile)
class ProfileAdmin(SingletonAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'tagline', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(VisitorCounter)
class VisitorCounterAdmin(SingletonAdminMixin, admin.ModelAdmin):
    list_display = ('count', 'updated_at')
    readonly_fields = ('updated_at',)
