from datetime import date

import pytest

from apps.certifications.models import CertificationDefinition, ExamSchedule
from apps.certifications.services.calendar import (
    build_month_calendar,
    get_tracked_certifications,
    get_upcoming_schedules,
)


@pytest.fixture
def national_cert(db) -> CertificationDefinition:
    return CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )


@pytest.fixture
def language_cert(db) -> CertificationDefinition:
    return CertificationDefinition.objects.create(
        name='토익', issuer='YBM', category=CertificationDefinition.Category.LANGUAGE, crawler_type='manual',
    )


@pytest.mark.django_db
def test_해당_월의_접수시작일에_배지가_붙는다(national_cert: CertificationDefinition) -> None:
    ExamSchedule.objects.create(
        certification=national_cert, round_name='2026년 1회 필기',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )

    weeks = build_month_calendar(2026, 1)

    matched_days = [day for week in weeks for day in week if day.day_date == date(2026, 1, 5)]
    assert len(matched_days) == 1
    assert matched_days[0].schedules[0]['certification_name'] == '정보처리기사'
    assert matched_days[0].schedules[0]['label'] == '접수시작'


@pytest.mark.django_db
def test_이전달_다음달_걸치는_날짜는_is_current_month가_False다() -> None:
    weeks = build_month_calendar(2026, 4)  # 2026-04-01은 수요일이라 첫 주에 3월 말일이 섞인다

    first_week = weeks[0]
    non_current = [day for day in first_week if not day.is_current_month]
    assert len(non_current) > 0
    assert all(day.day_date.month != 4 for day in non_current)


@pytest.mark.django_db
def test_카테고리로_필터링할_수_있다(
    national_cert: CertificationDefinition, language_cert: CertificationDefinition,
) -> None:
    ExamSchedule.objects.create(
        certification=national_cert, round_name='2026년 1회',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )
    ExamSchedule.objects.create(
        certification=language_cert, round_name='2026년 3회',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )

    weeks = build_month_calendar(2026, 1, category='language')

    matched_days = [day for week in weeks for day in week if day.day_date == date(2026, 1, 5)]
    names = [badge['certification_name'] for badge in matched_days[0].schedules]
    assert names == ['토익']


@pytest.mark.django_db
def test_다가오는_일정은_접수마감일_오름차순이다(national_cert: CertificationDefinition) -> None:
    ExamSchedule.objects.create(
        certification=national_cert, round_name='2회',
        registration_start=date(2026, 6, 1), registration_end=date(2026, 6, 5),
    )
    ExamSchedule.objects.create(
        certification=national_cert, round_name='1회',
        registration_start=date(2026, 1, 1), registration_end=date(2026, 1, 5),
    )

    result = get_upcoming_schedules(today=date(2025, 12, 1))

    assert [s.round_name for s in result] == ['1회', '2회']


@pytest.mark.django_db
def test_다가오는_일정은_접수마감이_지난_일정을_제외한다(national_cert: CertificationDefinition) -> None:
    ExamSchedule.objects.create(
        certification=national_cert, round_name='지난회차',
        registration_start=date(2026, 1, 1), registration_end=date(2026, 1, 5),
    )

    result = get_upcoming_schedules(today=date(2026, 2, 1))

    assert result == []


@pytest.mark.django_db
def test_추적_중인_자격증_목록은_비활성_자격증을_제외한다(
    national_cert: CertificationDefinition, language_cert: CertificationDefinition,
) -> None:
    CertificationDefinition.objects.create(
        name='비활성자격증', issuer='기관', category=CertificationDefinition.Category.ETC,
        crawler_type='manual', is_active=False,
    )

    result = get_tracked_certifications()

    names = {cert.name for cert in result}
    assert names == {'정보처리기사', '토익'}


@pytest.mark.django_db
def test_추적_중인_자격증_목록은_상시_접수_자격증도_포함한다() -> None:
    CertificationDefinition.objects.create(
        name='CCNA', issuer='Cisco', category=CertificationDefinition.Category.IT_PRIVATE,
        crawler_type='manual', is_always_open=True,
    )

    result = get_tracked_certifications(category='it_private')

    assert [cert.name for cert in result] == ['CCNA']
