from django.contrib import admin

from .models import CertificationDefinition, ExamSchedule


class ExamScheduleInline(admin.TabularInline):
    model = ExamSchedule
    extra = 0
    fields = (
        'round_name', 'registration_start', 'registration_end', 'exam_date',
        'result_announcement_date', 'source_url',
    )


@admin.register(CertificationDefinition)
class CertificationDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'issuer', 'category', 'crawler_type', 'is_always_open', 'is_active', 'order')
    list_filter = ('category', 'crawler_type', 'is_always_open', 'is_active')
    search_fields = ('name', 'issuer')
    inlines = (ExamScheduleInline,)


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'certification', 'round_name', 'registration_start', 'registration_end',
        'exam_date', 'registration_open_notified', 'registration_deadline_notified',
    )
    list_filter = ('certification', 'registration_open_notified', 'registration_deadline_notified')
    search_fields = ('round_name', 'certification__name')
    readonly_fields = ('registration_open_notified', 'registration_deadline_notified')
