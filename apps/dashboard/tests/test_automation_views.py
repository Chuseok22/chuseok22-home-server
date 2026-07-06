from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.core.models import ScheduledJobConfig

User = get_user_model()


@pytest.mark.django_db
def test_자동화_목록_페이지는_JOB_DEFINITIONS를_시딩해서_보여준다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('dashboard:automation-list'))

    assert response.status_code == 200
    assert ScheduledJobConfig.objects.filter(job_id='check_new_notices').exists()
    assert ScheduledJobConfig.objects.filter(job_id='fetch_github_activities').exists()


@pytest.mark.django_db
def test_자동화_설정_저장_스케줄러_비활성_환경() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    # automation_update가 저장 전 자동으로 get_or_seed_job_config를 호출해 시딩하지만,
    # 저장 후 값(9:30)과의 변화를 명확히 검증하기 위해 초기 cron_hour/minute을 직접 고정해 둔다.
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    client = Client()
    client.force_login(owner)

    # get_scheduler를 명시적으로 patch해 pytest 환경의 ENABLE_SCHEDULER 기본값에 의존하지 않는다.
    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=None):
        response = client.post(reverse('dashboard:automation-update', args=['check_new_notices']), {
            'is_enabled': 'on',
            'cron_hour': 9,
            'cron_minute': 30,
        })

    assert response.status_code == 200
    config = ScheduledJobConfig.objects.get(job_id='check_new_notices')
    assert config.cron_hour == 9
    assert config.cron_minute == 30
    assert config.is_enabled is True


@pytest.mark.django_db
def test_등록되지_않은_작업은_404() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:automation-update', args=['unknown_job']), {
        'is_enabled': 'on', 'cron_hour': 9, 'cron_minute': 0,
    })

    assert response.status_code == 404


@pytest.mark.django_db
def test_잘못된_시각값은_저장되지_않는다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    # automation_update가 저장 전 자동으로 시딩하지만, "검증 실패 시 기존 값이 그대로 유지되는지"를
    # 명확히 확인하기 위해 초기 cron_hour=8을 직접 고정해 둔다.
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:automation-update', args=['check_new_notices']), {
        'is_enabled': 'on',
        'cron_hour': 24,
        'cron_minute': 0,
    })

    assert response.status_code == 200
    config = ScheduledJobConfig.objects.get(job_id='check_new_notices')
    assert config.cron_hour == 8  # 기존 값 그대로 유지 (저장 실패)
