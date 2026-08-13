import logging

import requests
from django.conf import settings

from apps.certifications.models import ExamSchedule

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10


def send_registration_open_reminder(schedule: ExamSchedule) -> bool:
    """원서접수가 오늘 시작된 일정에 대한 알림을 보낸다."""
    message = (
        f'📝 [{schedule.certification.name}] {schedule.round_name} 원서접수 오늘 시작 '
        f'(~{schedule.registration_end:%m/%d})'
    )
    if schedule.source_url:
        message += f'\n🔗 {schedule.source_url}'
    return _send_admin_alert(message)


def send_registration_deadline_reminder(schedule: ExamSchedule) -> bool:
    """원서접수 마감이 임박한 일정에 대한 알림을 보낸다."""
    message = (
        f'⏰ [{schedule.certification.name}] {schedule.round_name} 원서접수 마감 임박 '
        f'({schedule.registration_end:%m/%d}까지)'
    )
    if schedule.source_url:
        message += f'\n🔗 {schedule.source_url}'
    return _send_admin_alert(message)


def _send_admin_alert(message: str) -> bool:
    webhook_url = settings.DISCORD_ADMIN_WEBHOOK_URL
    if not webhook_url:
        logger.warning('DISCORD_ADMIN_WEBHOOK_URL 미설정 — 자격증 알림을 건너뜁니다.')
        return False

    payload = {
        'content': message,
        # 자격증명·회차명에 @everyone/@here 등이 섞여 있어도 실제 멘션이 발생하지 않도록 차단
        'allowed_mentions': {'parse': []},
    }
    try:
        # 리디렉션을 따라가지 않는다 — 저장된 웹훅 URL이 다른 호스트로 리디렉션시켜 서버가
        # 임의의 내부/외부 주소에 요청을 보내는 SSRF 경로를 차단한다.
        response = requests.post(webhook_url, json=payload, timeout=_REQUEST_TIMEOUT, allow_redirects=False)
        response.raise_for_status()
        return True
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        logger.error('디스코드 자격증 알림 발송 실패 (status=%s)', status)
        return False
    except requests.RequestException as e:
        logger.error('디스코드 자격증 알림 발송 실패 (error_type=%s)', type(e).__name__)
        return False
