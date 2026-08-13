from datetime import date

import pytest
from django.db import IntegrityError

from apps.certifications.models import CertificationDefinition, ExamSchedule


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
