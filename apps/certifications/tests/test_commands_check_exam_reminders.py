from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.certifications.models import CertificationDefinition, ExamSchedule


@pytest.fixture
def certification(db) -> CertificationDefinition:
    return CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )


@pytest.mark.django_db
def test_오늘_접수_시작인_일정은_알림을_보내고_플래그를_갱신한다(certification: CertificationDefinition) -> None:
    today = timezone.localdate()
    schedule = ExamSchedule.objects.create(
        certification=certification, round_name='2026년 1회',
        registration_start=today, registration_end=today + timedelta(days=4),
    )

    with patch(
        'apps.certifications.management.commands.check_exam_reminders.send_registration_open_reminder',
        return_value=True,
    ) as mock_send:
        call_command('check_exam_reminders')

    mock_send.assert_called_once()
    schedule.refresh_from_db()
    assert schedule.registration_open_notified is True


@pytest.mark.django_db
def test_이미_알림을_보낸_일정은_다시_보내지_않는다(certification: CertificationDefinition) -> None:
    today = timezone.localdate()
    ExamSchedule.objects.create(
        certification=certification, round_name='2026년 1회',
        registration_start=today, registration_end=today + timedelta(days=4),
        registration_open_notified=True,
    )

    with patch(
        'apps.certifications.management.commands.check_exam_reminders.send_registration_open_reminder',
    ) as mock_send:
        call_command('check_exam_reminders')

    mock_send.assert_not_called()


@pytest.mark.django_db
def test_마감_3일_전인_일정은_임박_알림을_보낸다(certification: CertificationDefinition) -> None:
    today = timezone.localdate()
    schedule = ExamSchedule.objects.create(
        certification=certification, round_name='2026년 1회',
        registration_start=today - timedelta(days=10), registration_end=today + timedelta(days=3),
    )

    with patch(
        'apps.certifications.management.commands.check_exam_reminders.send_registration_deadline_reminder',
        return_value=True,
    ) as mock_send:
        call_command('check_exam_reminders')

    mock_send.assert_called_once()
    schedule.refresh_from_db()
    assert schedule.registration_deadline_notified is True


@pytest.mark.django_db
def test_비활성_자격증의_일정은_알림을_보내지_않는다(certification: CertificationDefinition) -> None:
    certification.is_active = False
    certification.save()
    today = timezone.localdate()
    ExamSchedule.objects.create(
        certification=certification, round_name='2026년 1회',
        registration_start=today, registration_end=today + timedelta(days=4),
    )

    with patch(
        'apps.certifications.management.commands.check_exam_reminders.send_registration_open_reminder',
    ) as mock_send:
        call_command('check_exam_reminders')

    mock_send.assert_not_called()


@pytest.mark.django_db
def test_상시_접수_자격증의_일정은_알림을_보내지_않는다(certification: CertificationDefinition) -> None:
    certification.is_always_open = True
    certification.save()
    today = timezone.localdate()
    ExamSchedule.objects.create(
        certification=certification, round_name='실수로_등록된_일정',
        registration_start=today, registration_end=today + timedelta(days=4),
    )

    with patch(
        'apps.certifications.management.commands.check_exam_reminders.send_registration_open_reminder',
    ) as mock_send:
        call_command('check_exam_reminders')

    mock_send.assert_not_called()
