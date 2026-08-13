from datetime import date
from unittest.mock import patch

from django.test import TestCase

from apps.certifications.models import CertificationDefinition, ExamSchedule
from apps.certifications.services.telegram_reminder import (
    send_registration_deadline_reminder,
    send_registration_open_reminder,
)


class TestSendRegistrationOpenReminder(TestCase):
    def test_메시지에_자격증명과_회차명과_마감일을_포함한다(self) -> None:
        cert = CertificationDefinition.objects.create(
            name='정보처리기사', issuer='한국산업인력공단',
            category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
        )
        schedule = ExamSchedule.objects.create(
            certification=cert, round_name='2026년 1회 필기',
            registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
            source_url='https://www.q-net.or.kr/crf021.do',
        )

        with patch(
            'apps.certifications.services.telegram_reminder.TelegramService.send_admin_alert',
        ) as mock_send:
            mock_send.return_value = True
            result = send_registration_open_reminder(schedule)

        assert result is True
        message = mock_send.call_args.args[0]
        assert '정보처리기사' in message
        assert '2026년 1회 필기' in message
        assert '01/09' in message
        assert schedule.source_url in message


class TestSendRegistrationDeadlineReminder(TestCase):
    def test_메시지에_마감일을_포함한다(self) -> None:
        cert = CertificationDefinition.objects.create(
            name='SQLD', issuer='한국데이터산업진흥원',
            category=CertificationDefinition.Category.IT_PRIVATE, crawler_type='manual',
        )
        schedule = ExamSchedule.objects.create(
            certification=cert, round_name='2026년 2회',
            registration_start=date(2026, 3, 1), registration_end=date(2026, 3, 5),
        )

        with patch(
            'apps.certifications.services.telegram_reminder.TelegramService.send_admin_alert',
        ) as mock_send:
            mock_send.return_value = True
            result = send_registration_deadline_reminder(schedule)

        assert result is True
        message = mock_send.call_args.args[0]
        assert 'SQLD' in message
        assert '03/05' in message
