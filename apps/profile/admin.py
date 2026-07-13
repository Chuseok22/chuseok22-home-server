from django.contrib import admin
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


class SingletonAdminMixin:
    """이미 레코드가 하나라도 있으면 Admin에서 추가 화면을 차단하는 믹스인 (싱글턴 모델 전용)."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return super().has_add_permission(request) and not self.model.objects.exists()


@admin.register(Profile)
class ProfileAdmin(SingletonAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'tagline', 'updated_at')
    readonly_fields = ('updated_at',)


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
