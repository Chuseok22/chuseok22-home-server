from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.certifications.models import CertificationDefinition, ExamSchedule
from apps.certifications.services.discord_reminder import (
    send_registration_deadline_reminder,
    send_registration_open_reminder,
)


@override_settings(DISCORD_ADMIN_WEBHOOK_URL='https://discord.com/api/webhooks/1/a')
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

        with patch('apps.certifications.services.discord_reminder.requests.post') as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.raise_for_status.return_value = None
            result = send_registration_open_reminder(schedule)

        assert result is True
        payload = mock_post.call_args.kwargs['json']
        message = payload['content']
        assert '정보처리기사' in message
        assert '2026년 1회 필기' in message
        assert '01/09' in message
        assert schedule.source_url in message
        assert payload['allowed_mentions'] == {'parse': []}
        assert mock_post.call_args.args[0] == 'https://discord.com/api/webhooks/1/a'
        assert mock_post.call_args.kwargs['allow_redirects'] is False


@override_settings(DISCORD_ADMIN_WEBHOOK_URL='https://discord.com/api/webhooks/1/a')
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

        with patch('apps.certifications.services.discord_reminder.requests.post') as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.raise_for_status.return_value = None
            result = send_registration_deadline_reminder(schedule)

        assert result is True
        message = mock_post.call_args.kwargs['json']['content']
        assert 'SQLD' in message
        assert '03/05' in message


@override_settings(DISCORD_ADMIN_WEBHOOK_URL='')
class TestSendReminderMissingWebhook(TestCase):
    def test_웹훅_미설정시_건너뛴다(self) -> None:
        cert = CertificationDefinition.objects.create(
            name='SQLD', issuer='한국데이터산업진흥원',
            category=CertificationDefinition.Category.IT_PRIVATE, crawler_type='manual',
        )
        schedule = ExamSchedule.objects.create(
            certification=cert, round_name='2026년 2회',
            registration_start=date(2026, 3, 1), registration_end=date(2026, 3, 5),
        )

        with patch('apps.certifications.services.discord_reminder.requests.post') as mock_post:
            result = send_registration_open_reminder(schedule)

        assert result is False
        mock_post.assert_not_called()
