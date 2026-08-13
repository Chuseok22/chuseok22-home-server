from apps.certifications.models import ExamSchedule
from apps.notifications.services.telegram import TelegramService


def send_registration_open_reminder(schedule: ExamSchedule) -> bool:
    """원서접수가 오늘 시작된 일정에 대한 알림을 보낸다."""
    message = (
        f'📝 [{schedule.certification.name}] {schedule.round_name} 원서접수 오늘 시작 '
        f'(~{schedule.registration_end:%m/%d})'
    )
    if schedule.source_url:
        message += f'\n🔗 {schedule.source_url}'
    return TelegramService().send_admin_alert(message)


def send_registration_deadline_reminder(schedule: ExamSchedule) -> bool:
    """원서접수 마감이 임박한 일정에 대한 알림을 보낸다."""
    message = (
        f'⏰ [{schedule.certification.name}] {schedule.round_name} 원서접수 마감 임박 '
        f'({schedule.registration_end:%m/%d}까지)'
    )
    if schedule.source_url:
        message += f'\n🔗 {schedule.source_url}'
    return TelegramService().send_admin_alert(message)
