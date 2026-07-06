from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.core.models import ScheduledJobConfig


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_저장_시_update_job_schedule이_호출된다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'cron_hour': 10,
            'cron_minute': 30,
            '_save': 'Save',
        })

    assert response.status_code == 302
    mock_update.assert_called_once_with('check_new_notices', is_enabled=True, hour=10, minute=30)


@pytest.mark.django_db
def test_새_행_추가는_허용되지_않는다(admin_client: Client) -> None:
    url = reverse('admin:core_scheduledjobconfig_add')
    response = admin_client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_스케줄러_비활성_상태면_경고_메시지가_노출된다(admin_client: Client) -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    url = reverse('admin:core_scheduledjobconfig_changelist')

    with patch('apps.core.admin.get_scheduler', return_value=None):
        response = admin_client.get(url)

    messages = [m.message for m in response.context['messages']]
    assert any('스케줄러가 비활성화' in m for m in messages)
