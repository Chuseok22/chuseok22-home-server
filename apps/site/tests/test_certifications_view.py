from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.certifications.models import CertificationDefinition, ExamSchedule


@pytest.mark.django_db
def test_자격증_캘린더_페이지는_다가오는_일정을_보여준다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='manual',
    )
    today = timezone.localdate()
    ExamSchedule.objects.create(
        certification=cert, round_name='2026년 1회',
        registration_start=today, registration_end=today + timedelta(days=10),
    )

    client = Client()
    response = client.get(reverse('site:certifications'))

    assert response.status_code == 200
    assert '정보처리기사' in response.content.decode()


@pytest.mark.django_db
def test_카테고리로_필터링할_수_있다() -> None:
    today = timezone.localdate()
    national = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='manual',
    )
    language = CertificationDefinition.objects.create(
        name='토익', issuer='YBM', category=CertificationDefinition.Category.LANGUAGE, crawler_type='manual',
    )
    ExamSchedule.objects.create(
        certification=national, round_name='2026년 1회',
        registration_start=today, registration_end=today + timedelta(days=10),
    )
    ExamSchedule.objects.create(
        certification=language, round_name='2026년 5회',
        registration_start=today, registration_end=today + timedelta(days=10),
    )

    client = Client()
    response = client.get(reverse('site:certifications'), {'category': 'national_tech'})
    body = response.content.decode()

    assert '정보처리기사' in body
    assert '토익' not in body


@pytest.mark.django_db
def test_year_month으로_다른_달을_조회할_수_있다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='manual',
    )
    ExamSchedule.objects.create(
        certification=cert, round_name='2026년 1회',
        registration_start=date(2026, 1, 5), registration_end=date(2026, 1, 9),
    )

    client = Client()
    response = client.get(reverse('site:certifications'), {'year': 2026, 'month': 1})

    assert response.status_code == 200
    assert response.context['year'] == 2026
    assert response.context['month'] == 1


@pytest.mark.django_db
def test_범위를_벗어난_year는_오늘_기준으로_폴백한다() -> None:
    today = timezone.localdate()

    client = Client()
    response = client.get(reverse('site:certifications'), {'year': 9999, 'month': 12})

    assert response.status_code == 200
    assert response.context['year'] == today.year
    assert response.context['month'] == today.month


@pytest.mark.django_db
def test_마감_D3_이하_일정은_강조_배지_클래스가_붙는다() -> None:
    cert = CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='manual',
    )
    other_cert = CertificationDefinition.objects.create(
        name='토익', issuer='YBM', category=CertificationDefinition.Category.LANGUAGE, crawler_type='manual',
    )
    today = timezone.localdate()
    ExamSchedule.objects.create(
        certification=cert, round_name='마감임박 회차',
        registration_start=today, registration_end=today + timedelta(days=2),
    )
    ExamSchedule.objects.create(
        certification=other_cert, round_name='여유 회차',
        registration_start=today, registration_end=today + timedelta(days=10),
    )

    client = Client()
    response = client.get(reverse('site:certifications'))
    body = response.content.decode()

    assert '!bg-error !text-error-content">D-2</span>' in body
    assert '!bg-error !text-error-content">D-10</span>' not in body


@pytest.mark.django_db
def test_매우_긴_숫자_문자열의_year는_오늘_기준으로_폴백한다() -> None:
    # int()는 Python 3.11+부터 4300자리 넘는 십진수 문자열 변환을 ValueError로 거부한다 —
    # isdecimal()만으로 걸러지지 않으므로 500이 아니라 정상 폴백돼야 한다.
    today = timezone.localdate()
    huge_digits = '9' * 5000

    client = Client()
    response = client.get(reverse('site:certifications'), {'year': huge_digits, 'month': huge_digits})

    assert response.status_code == 200
    assert response.context['year'] == today.year
    assert response.context['month'] == today.month


@pytest.mark.django_db
def test_상시_접수_자격증은_추적_목록에_상시_접수로_표시된다() -> None:
    CertificationDefinition.objects.create(
        name='CCNA', issuer='Cisco', category=CertificationDefinition.Category.IT_PRIVATE,
        crawler_type='manual', is_always_open=True,
    )

    client = Client()
    response = client.get(reverse('site:certifications'))
    body = response.content.decode()

    assert 'CCNA' in body
    assert '상시 접수' in body
