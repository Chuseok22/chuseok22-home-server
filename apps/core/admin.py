from typing import Any

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse

from apps.core.models import ScheduledJobConfig
from apps.core.scheduler import JOB_DEFINITIONS, get_scheduler
from apps.core.services.scheduler_service import update_job_schedule


@admin.register(ScheduledJobConfig)
class ScheduledJobConfigAdmin(admin.ModelAdmin):
    list_display = ('label', 'is_enabled', 'cron_hour', 'cron_minute', 'updated_at')
    readonly_fields = ('job_id', 'updated_at')

    @admin.display(description='작업')
    def label(self, obj: ScheduledJobConfig) -> str:
        return JOB_DEFINITIONS.get(obj.job_id, {}).get('label', obj.job_id)

    def has_add_permission(self, request: HttpRequest) -> bool:
        # job_id는 JOB_DEFINITIONS와 1:1로 시딩되는 값이라 임의 생성을 막는다.
        return False

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        if get_scheduler() is None:
            self.message_user(
                request,
                '스케줄러가 비활성화 상태입니다 (ENABLE_SCHEDULER=False). 변경 사항은 DB에만 저장되고 다음 기동 시 반영됩니다.',
                level=messages.WARNING,
            )
        return super().changelist_view(request, extra_context)

    def save_model(
        self,
        request: HttpRequest,
        obj: ScheduledJobConfig,
        form: forms.ModelForm,
        change: bool,
    ) -> None:
        # 기본 obj.save() 대신 기존 서비스 레이어를 재사용해 DB 저장 + 실행 중 스케줄러 즉시 반영을 함께 처리한다.
        update_job_schedule(
            obj.job_id,
            is_enabled=obj.is_enabled,
            hour=obj.cron_hour,
            minute=obj.cron_minute,
        )
