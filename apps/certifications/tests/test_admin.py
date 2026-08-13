from datetime import date

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.certifications.models import CertificationDefinition, ExamSchedule, NotificationSettings


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(  # noqa: S106 - force_login()만 쓰므로 실제 인증에 사용되지 않는 테스트 전용 값
        username='admin', email='admin@example.com', password='pw12345!',
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_자격증_목록_화면은_200을_반환한다(admin_client: Client) -> None:
    CertificationDefinition.objects.create(
        name='정보처리기사', issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH, crawler_type='hrdkorea_api',
    )

    response = admin_client.get(reverse('admin:certifications_certificationdefinition_changelist'))

    assert response.status_code == 200
    assert '정보처리기사' in response.content.decode()


@pytest.mark.django_db
def test_시험일정_목록_화면은_200을_반환한다(admin_client: Client) -> None:
    cert = CertificationDefinition.objects.create(
        name='SQLD', issuer='한국데이터산업진흥원',
        category=CertificationDefinition.Category.IT_PRIVATE, crawler_type='manual',
    )
    ExamSchedule.objects.create(
        certification=cert, round_name='2026년 1회',
        registration_start=date(2026, 3, 1), registration_end=date(2026, 3, 5),
    )

    response = admin_client.get(reverse('admin:certifications_examschedule_changelist'))

    assert response.status_code == 200
    assert 'SQLD' in response.content.decode()


@pytest.mark.django_db
def test_notificationsettings가_이미_있으면_admin_추가_화면이_차단된다(admin_client: Client) -> None:
    NotificationSettings.objects.create(discord_webhook_url='https://discord.com/api/webhooks/1/a')

    response = admin_client.get(reverse('admin:certifications_notificationsettings_add'))

    assert response.status_code == 403
