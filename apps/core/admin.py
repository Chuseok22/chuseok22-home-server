from typing import Any

from apscheduler.jobstores.base import JobLookupError
from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse

from apps.core.models import (
    CRON_DAY_OF_WEEK_CHOICES,
    SCHEDULE_MODE_CHOICES,
    ScheduledJobConfig,
    WEEKDAY_TOKENS,
)
from apps.core.scheduler import JOB_DEFINITIONS, get_scheduler
from apps.core.services.scheduler_service import update_job_schedule

WEEKDAY_LABELS = [(token, label) for token, label in CRON_DAY_OF_WEEK_CHOICES if token != '*']

# GitHub API를 호출하는 잡에만 해당하는 안내 — 다른 잡(공지사항 크롤링, 이미지 정리)에는 무관하므로
# 전체 Meta.help_texts가 아니라 __init__에서 job_id를 보고 조건부로 붙인다.
_GITHUB_API_JOB_IDS = {'fetch_github_activities', 'fetch_github_stats'}
_GITHUB_API_RATE_LIMIT_HELP_TEXT = (
    'GitHub API 한도(REST 시간당 5,000회, GraphQL 시간당 5,000포인트) 대비 '
    '이 잡의 요청량은 실행당 최대 4회로 매우 적어, 1시간마다로 설정해도 안전합니다.'
)


class ScheduledJobConfigForm(forms.ModelForm):
    # 모델 필드의 blank=True 때문에 ModelForm이 자동 생성하는 필드는 빈 선택지("---------")를
    # 포함하게 되므로(Field.formfield()의 include_blank 동작), 명시적으로 선언해 이를 차단한다.
    schedule_mode = forms.ChoiceField(
        choices=SCHEDULE_MODE_CHOICES,
        widget=forms.RadioSelect,
        label='스케줄 모드',
    )
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_LABELS,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='요일',
    )
    fixed_hour_list = forms.MultipleChoiceField(
        choices=[(str(h), f'{h}시') for h in range(24)],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='실행 시각 (특정 시각 모드)',
    )

    class Meta:
        model = ScheduledJobConfig
        # cron_day_of_week, fixed_hours는 여기서 제외한다 — weekdays/fixed_hour_list 체크박스로만
        # 입력받고, clean()에서 콤마 문자열로 합성해 clean()에서 인스턴스에 직접 반영한다.
        fields = ['is_enabled', 'schedule_mode', 'interval_hours', 'interval_minute', 'fixed_minute']

    class Media:
        js = ('core/admin/schedule_mode_toggle.js',)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        instance: ScheduledJobConfig | None = kwargs.get('instance')
        if instance and instance.pk:
            self.fields['weekdays'].initial = (
                WEEKDAY_TOKENS if instance.cron_day_of_week == '*'
                else instance.cron_day_of_week.split(',')
            )
            self.fields['fixed_hour_list'].initial = (
                instance.fixed_hours.split(',') if instance.fixed_hours else []
            )
            if instance.job_id in _GITHUB_API_JOB_IDS:
                self.fields['interval_hours'].help_text = _GITHUB_API_RATE_LIMIT_HELP_TEXT

    def clean(self) -> dict[str, Any]:
        # cron_day_of_week/fixed_hours는 Meta.fields에 없어 ModelForm의 construct_instance()가
        # 건드리지 않는다 — 여기서 self.instance에 직접 반영해야 뒤이은 _post_clean()의
        # instance.full_clean()이 신규 제출값 기준으로 검증한다(save()에서 반영하면 이미 검증이
        # 끝난 뒤라 너무 늦음).
        #
        # 중요: weekdays/fixed_hour_list가 비어 제출되면(체크박스를 전부 해제) 절대로
        # self.instance.cron_day_of_week/fixed_hours를 빈 문자열로 덮어써서는 안 된다.
        # 이 두 필드는 Meta.fields에 없는 "폼 필드가 아닌 모델 필드"라서, 만약 인스턴스에
        # 빈 값을 넣은 채로 _post_clean()의 instance.full_clean()이 돌면 ScheduledJobConfig.clean()이
        # {'fixed_hours': ...}/{'cron_day_of_week': ...} 형태로 ValidationError를 던지는데,
        # Django의 BaseModelForm._update_errors()는 이를 폼 필드 이름이 아닌 키로 add_error(None, ...)에
        # 넘기고, Form.add_error()는 self.fields에 없는 키를 보면 ValueError를 던져 500으로 이어진다
        # (django/forms/forms.py의 add_error 구현 참고). 아래처럼 값이 있을 때만 인스턴스를 갱신하고,
        # 비어있으면 self.add_error()로 폼 에러만 남기고 인스턴스의 기존(저장된) 값은 그대로 둔다 —
        # 이 폼은 add 뷰가 막혀 있어(has_add_permission=False) 인스턴스가 항상 기존 값을 갖고 있으므로
        # 안전하다.
        cleaned = super().clean()
        weekdays = cleaned.get('weekdays') or []
        if weekdays:
            self.instance.cron_day_of_week = (
                '*' if set(weekdays) == set(WEEKDAY_TOKENS)
                else ','.join(sorted(weekdays, key=WEEKDAY_TOKENS.index))
            )
        # weekdays가 비어있으면 여기서 아무것도 하지 않는다 — weekdays 필드 자체가 required=True라
        # 이미 "이 필드는 필수 항목입니다" 폼 에러가 붙어 있고(is_valid()는 False), 인스턴스의
        # cron_day_of_week는 갱신 전 값 그대로 남아 model.full_clean()을 통과한다.

        if cleaned.get('schedule_mode') == 'fixed_times':
            hours = sorted((cleaned.get('fixed_hour_list') or []), key=int)
            if not hours:
                self.add_error('fixed_hour_list', '최소 1개 시각을 선택해야 합니다.')
                # hours가 비었으면 self.instance.fixed_hours를 건드리지 않는다(위와 동일한 이유).
            else:
                self.instance.fixed_hours = ','.join(hours)
        else:
            self.instance.fixed_hours = ''
        return cleaned


@admin.register(ScheduledJobConfig)
class ScheduledJobConfigAdmin(admin.ModelAdmin):
    form = ScheduledJobConfigForm
    list_display = ('label', 'is_enabled', 'schedule_summary', 'updated_at')
    readonly_fields = ('job_id', 'updated_at')

    @admin.display(description='작업')
    def label(self, obj: ScheduledJobConfig) -> str:
        return JOB_DEFINITIONS.get(obj.job_id, {}).get('label', obj.job_id)

    @admin.display(description='스케줄')
    def schedule_summary(self, obj: ScheduledJobConfig) -> str:
        if obj.schedule_mode == 'interval':
            core = f'{obj.interval_hours}시간마다 :{obj.interval_minute:02d}'
        else:
            hours = '/'.join(f'{int(h):02d}' for h in obj.fixed_hours.split(',')) if obj.fixed_hours else '-'
            core = f'{hours}시 :{obj.fixed_minute:02d}'
        day_label = '매일' if obj.cron_day_of_week == '*' else obj.cron_day_of_week
        return f'{core}, {day_label}'

    def has_add_permission(self, request: HttpRequest) -> bool:
        # job_id는 JOB_DEFINITIONS와 1:1로 시딩되는 값이라 임의 생성을 막는다.
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ScheduledJobConfig | None = None
    ) -> bool:
        # 삭제 시 update_job_schedule의 job_id 조회가 깨지므로 삭제도 막는다.
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
        try:
            update_job_schedule(
                obj.job_id,
                is_enabled=obj.is_enabled,
                schedule_mode=obj.schedule_mode,
                day_of_week=obj.cron_day_of_week,
                interval_hours=obj.interval_hours,
                interval_minute=obj.interval_minute,
                fixed_hours=obj.fixed_hours,
                fixed_minute=obj.fixed_minute,
            )
        except JobLookupError:
            # update_job_schedule 내부에서 DB 저장은 이미 완료된 상태 — 실행 중 스케줄러에
            # 해당 job_id가 등록되어 있지 않아 즉시 반영만 실패한 경우, 500 대신 경고로 안내한다.
            self.message_user(
                request,
                '설정은 저장되었지만 실행 중인 스케줄러에 해당 작업이 등록되어 있지 않아 '
                '즉시 반영하지 못했습니다. 다음 서버 재기동 시 반영됩니다.',
                level=messages.WARNING,
            )
