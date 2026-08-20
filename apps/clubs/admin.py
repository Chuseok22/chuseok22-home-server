from django.contrib import admin
from django.http import HttpRequest

from .models import RecruitmentDetection, TrackedClub


@admin.register(TrackedClub)
class TrackedClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'is_recruiting_now', 'last_checked_at', 'consecutive_failure_count')
    list_filter = ('is_active', 'is_recruiting_now')
    readonly_fields = (
        'is_recruiting_now', 'last_checked_at', 'consecutive_failure_count', 'failure_alert_sent', 'created_at',
    )


@admin.register(RecruitmentDetection)
class RecruitmentDetectionAdmin(admin.ModelAdmin):
    list_display = ('tracked_club', 'application_start', 'application_end', 'notify_succeeded', 'detected_at')
    list_filter = ('tracked_club', 'notify_succeeded')
    readonly_fields = (
        'tracked_club', 'application_start', 'application_end', 'apply_url', 'evidence_quote',
        'notify_succeeded', 'detected_at',
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        # 알림 발송 이력이라 수동 생성을 막는다 (apps.cinema.OpenedShowDateAdmin과 동일 패턴).
        return False
