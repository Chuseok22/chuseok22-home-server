from datetime import date
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.certifications.crawlers.base import ExamRoundItem
from apps.certifications.models import CertificationDefinition, ExamSchedule


@pytest.mark.django_db
def test_manual_자격증은_건너뛴다() -> None:
    CertificationDefinition.objects.create(
        name='SQLD', issuer='한국데이터산업진흥원',
        category=CertificationDefinition.Category.IT_PRIVATE, crawler_type='manual',
    )

    with patch('apps.certifications.management.commands.sync_exam_schedules.get_crawler') as mock_get_crawler:
        call_command('sync_exam_schedules')

    mock_get_crawler.assert_not_called()


@pytest.mark.django_db
def test_비활성_자격증은_건너뛴다() -> None:
    CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
        crawler_source_id='1320', is_active=False,
    )

    with patch('apps.certifications.management.commands.sync_exam_schedules.get_crawler') as mock_get_crawler:
        call_command('sync_exam_schedules')

    mock_get_crawler.assert_not_called()


@pytest.mark.django_db
def test_크롤링_결과로_examschedule을_생성한다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
        crawler_source_id='1320',
    )
    mock_crawler = type('MockCrawler', (), {
        'crawl': lambda self, source_id: [
            ExamRoundItem(
                round_name='2026년 1회 필기',
                registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
                exam_date=date(2026, 2, 7), result_announcement_date=date(2026, 3, 4),
                source_url='https://www.q-net.or.kr/crf021.do',
            ),
        ],
    })()

    with patch(
        'apps.certifications.management.commands.sync_exam_schedules.get_crawler', return_value=mock_crawler,
    ):
        call_command('sync_exam_schedules')

    schedule = ExamSchedule.objects.get(certification=cert, round_name='2026년 1회 필기')
    assert schedule.registration_start == date(2026, 1, 5)
    assert schedule.exam_date == date(2026, 2, 7)


@pytest.mark.django_db
def test_기존_일정의_notified_플래그는_재동기화해도_유지된다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
        crawler_source_id='1320',
    )
    ExamSchedule.objects.create(
        certification=cert, round_name='2026년 1회 필기',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
        registration_open_notified=True,
    )
    mock_crawler = type('MockCrawler', (), {
        'crawl': lambda self, source_id: [
            ExamRoundItem(
                round_name='2026년 1회 필기',
                registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 10),  # 마감일만 변경
                exam_date=None, result_announcement_date=None, source_url='',
            ),
        ],
    })()

    with patch(
        'apps.certifications.management.commands.sync_exam_schedules.get_crawler', return_value=mock_crawler,
    ):
        call_command('sync_exam_schedules')

    schedule = ExamSchedule.objects.get(certification=cert, round_name='2026년 1회 필기')
    assert schedule.registration_end == date(2026, 1, 10)
    assert schedule.registration_open_notified is True
