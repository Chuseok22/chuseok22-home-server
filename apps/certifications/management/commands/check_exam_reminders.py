from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.certifications.models import ExamSchedule
from apps.certifications.services.discord_reminder import (
    send_registration_deadline_reminder,
    send_registration_open_reminder,
)

_DEADLINE_REMINDER_DAYS_BEFORE = 3


class Command(BaseCommand):
    help = '원서접수 시작일/마감 임박(D-3) 자격증 일정을 디스코드로 알린다'

    def handle(self, *args, **options) -> None:
        today = timezone.localdate()
        self._send_open_reminders(today)
        self._send_deadline_reminders(today)

    def _send_open_reminders(self, today: date) -> None:
        schedules = ExamSchedule.objects.filter(
            certification__is_active=True,
            certification__is_always_open=False,
            registration_start=today,
            registration_open_notified=False,
        ).select_related('certification')
        for schedule in schedules:
            if send_registration_open_reminder(schedule):
                schedule.registration_open_notified = True
                schedule.save(update_fields=['registration_open_notified'])
                self.stdout.write(f'접수 시작 알림 발송: {schedule.certification.name} {schedule.round_name}')

    def _send_deadline_reminders(self, today: date) -> None:
        deadline_target = today + timedelta(days=_DEADLINE_REMINDER_DAYS_BEFORE)
        schedules = ExamSchedule.objects.filter(
            certification__is_active=True,
            certification__is_always_open=False,
            registration_end=deadline_target,
            registration_deadline_notified=False,
        ).select_related('certification')
        for schedule in schedules:
            if send_registration_deadline_reminder(schedule):
                schedule.registration_deadline_notified = True
                schedule.save(update_fields=['registration_deadline_notified'])
                self.stdout.write(f'접수 마감 임박 알림 발송: {schedule.certification.name} {schedule.round_name}')
