from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.certifications.models import CertificationDefinition, ExamSchedule, NotificationSettings


def test_certification_definition_기본값() -> None:
    definition = CertificationDefinition(
        name='정보처리기사',
        issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH,
        crawler_type='hrdkorea_api',
    )

    assert definition.is_active is True
    assert definition.order == 0
    assert definition.crawler_source_id == ''
    assert definition.is_always_open is False
    assert str(definition) == '정보처리기사'


@pytest.mark.django_db
def test_certification_definition_정렬은_order_다음_name_순이다() -> None:
    CertificationDefinition.objects.create(
        name='나중자격증', issuer='기관', category=CertificationDefinition.Category.ETC,
        crawler_type='manual', order=1,
    )
    CertificationDefinition.objects.create(
        name='먼저자격증', issuer='기관', category=CertificationDefinition.Category.ETC,
        crawler_type='manual', order=0,
    )

    names = list(CertificationDefinition.objects.values_list('name', flat=True))

    assert names == ['먼저자격증', '나중자격증']


@pytest.mark.django_db
def test_exam_schedule_기본값() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )

    schedule = ExamSchedule.objects.create(
        certification=cert, round_name='2026년 1회 필기',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )

    assert schedule.exam_date is None
    assert schedule.result_announcement_date is None
    assert schedule.registration_open_notified is False
    assert schedule.registration_deadline_notified is False


@pytest.mark.django_db
def test_exam_schedule_같은_자격증_같은_회차명은_중복될_수_없다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )
    ExamSchedule.objects.create(
        certification=cert, round_name='2026년 1회 필기',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )

    with pytest.raises(IntegrityError):
        ExamSchedule.objects.create(
            certification=cert, round_name='2026년 1회 필기',
            registration_start=date(2026, 1, 6), registration_end=date(2026, 1, 10),
        )


@pytest.mark.django_db
def test_exam_schedule_접수_마감일이_시작일보다_빠르면_DB에서_거부된다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )

    with pytest.raises(IntegrityError):
        ExamSchedule.objects.create(
            certification=cert, round_name='역전된_일정',
            registration_start=date(2026, 1, 9), registration_end=date(2026, 1, 5),
        )


@pytest.mark.django_db
def test_exam_schedule_정렬은_접수시작일_오름차순이다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )
    ExamSchedule.objects.create(
        certification=cert, round_name='2회', registration_start=date(2026, 6, 1), registration_end=date(2026, 6, 5),
    )
    ExamSchedule.objects.create(
        certification=cert, round_name='1회', registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )

    round_names = list(ExamSchedule.objects.values_list('round_name', flat=True))

    assert round_names == ['1회', '2회']


def test_notification_settings_기본값() -> None:
    settings = NotificationSettings()

    assert settings.discord_webhook_url == ''
    assert str(settings) == '자격증 알림 설정'


@pytest.mark.django_db
def test_notification_settings_discord_웹훅이_아닌_url은_거부된다() -> None:
    settings = NotificationSettings(discord_webhook_url='https://evil.example.com/api/webhooks/1/a')

    with pytest.raises(ValidationError):
        settings.full_clean()


@pytest.mark.django_db
def test_notification_settings_유효한_discord_웹훅_url은_통과한다() -> None:
    settings = NotificationSettings(discord_webhook_url='https://discord.com/api/webhooks/1/a')

    settings.full_clean()  # 예외가 발생하지 않으면 통과
