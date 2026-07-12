from unittest.mock import MagicMock, patch

import pytest
from apscheduler.jobstores.base import JobLookupError
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


def test_schedule_mode_필드에_빈_선택지가_없다() -> None:
    from apps.core.admin import ScheduledJobConfigForm

    form = ScheduledJobConfigForm()
    choice_values = [value for value, _label in form.fields['schedule_mode'].choices]
    assert '' not in choice_values
    assert form.fields['schedule_mode'].required is True


@pytest.mark.django_db
def test_fixed_times_모드로_저장_시_update_job_schedule이_호출된다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'fixed_times',
            'fixed_hour_list': ['9', '15'],
            'fixed_minute': 30,
            'interval_minute': 0,
            'weekdays': ['mon'],
            '_save': 'Save',
        })

    assert response.status_code == 302
    mock_update.assert_called_once_with(
        'check_new_notices', is_enabled=True, schedule_mode='fixed_times', day_of_week='mon',
        interval_hours=None, interval_minute=0, fixed_hours='9,15', fixed_minute=30,
    )


@pytest.mark.django_db
def test_interval_모드로_저장_시_update_job_schedule이_호출된다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='fetch_github_activities', schedule_mode='interval', interval_hours=3,
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'interval',
            'interval_hours': 6,
            'interval_minute': 0,
            'fixed_minute': 0,
            'weekdays': ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
            '_save': 'Save',
        })

    assert response.status_code == 302
    mock_update.assert_called_once_with(
        'fetch_github_activities', is_enabled=True, schedule_mode='interval', day_of_week='*',
        interval_hours=6, interval_minute=0, fixed_hours='', fixed_minute=0,
    )


@pytest.mark.django_db
def test_fixed_times_모드에서_시각을_하나도_선택하지_않으면_검증_오류가_발생한다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'fixed_times',
            'fixed_minute': 0,
            'interval_minute': 0,
            'weekdays': ['mon'],
            '_save': 'Save',
        })

    assert response.status_code == 200
    mock_update.assert_not_called()


@pytest.mark.django_db
def test_interval_행을_fixed_times_무선택으로_전환해도_500이_없다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='fetch_github_activities', schedule_mode='interval',
        interval_hours=3, fixed_hours='',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'fixed_times',
            'fixed_minute': 0,
            'interval_minute': 0,
            'weekdays': ['mon'],
            '_save': 'Save',
        })

    assert response.status_code == 200
    mock_update.assert_not_called()


@pytest.mark.django_db
def test_요일을_하나도_선택하지_않으면_500_없이_검증_오류가_발생한다(admin_client: Client) -> None:
    # weekdays가 비어도 clean()이 인스턴스의 기존 cron_day_of_week를 덮어쓰지 않아야 한다.
    # 덮어쓰면 _post_clean()의 instance.full_clean()이 폼 필드가 아닌 cron_day_of_week에 대해
    # ValidationError를 던지고, Django가 이를 ValueError로 승격시켜 500이 난다.
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8', cron_day_of_week='mon',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'fixed_times',
            'fixed_hour_list': ['8'],
            'fixed_minute': 0,
            'interval_minute': 0,
            '_save': 'Save',
        })

    assert response.status_code == 200
    mock_update.assert_not_called()


@pytest.mark.django_db
def test_schedule_mode를_빈_값으로_제출하면_500_없이_검증_오류가_발생한다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': '',
            'fixed_hour_list': ['8'],
            'fixed_minute': 0,
            'interval_minute': 0,
            'weekdays': ['mon'],
            '_save': 'Save',
        })

    assert response.status_code == 200
    mock_update.assert_not_called()


@pytest.mark.django_db
def test_interval_minute를_생략하면_500_없이_검증_오류가_발생한다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    with patch('apps.core.admin.update_job_schedule') as mock_update:
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'fixed_times',
            'fixed_hour_list': ['8'],
            'fixed_minute': 0,
            # interval_minute 의도적으로 생략
            'weekdays': ['mon'],
            '_save': 'Save',
        })

    assert response.status_code == 200
    mock_update.assert_not_called()


@pytest.mark.django_db
def test_새_행_추가는_허용되지_않는다(admin_client: Client) -> None:
    url = reverse('admin:core_scheduledjobconfig_add')
    response = admin_client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_행_삭제는_허용되지_않는다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(job_id='check_new_notices', fixed_hours='8')
    url = reverse('admin:core_scheduledjobconfig_delete', args=[config.pk])
    response = admin_client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_스케줄러에_job이_없으면_경고_메시지가_노출되고_저장은_유지된다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    # update_job_schedule 전체를 목으로 대체하면 실제 config.save()가 실행되지 않아
    # "저장은 유지된다"는 이 테스트 이름의 주장을 검증하지 못한다. 실제 update_job_schedule이
    # 그대로 실행되도록 두고, 그 내부에서 호출하는 scheduler.reschedule_job()만 실패시킨다.
    mock_scheduler = MagicMock()
    mock_scheduler.reschedule_job.side_effect = JobLookupError(config.job_id)
    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=mock_scheduler):
        response = admin_client.post(url, {
            'is_enabled': 'on',
            'schedule_mode': 'fixed_times',
            'fixed_hour_list': ['9'],
            'fixed_minute': 0,
            'interval_minute': 0,
            'weekdays': ['mon'],
            '_save': 'Save',
        }, follow=True)

    assert response.status_code == 200
    messages = [m.message for m in response.context['messages']]
    assert any('즉시 반영하지 못했습니다' in m for m in messages)

    # 실제 config.save()가 실행되어 제출된 값이 반영됐는지 확인한다(스케줄러 반영 실패와 무관하게).
    config.refresh_from_db()
    assert config.fixed_hours == '9'
    assert config.cron_day_of_week == 'mon'


@pytest.mark.django_db
def test_스케줄러_비활성_상태면_경고_메시지가_노출된다(admin_client: Client) -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', fixed_hours='8')
    url = reverse('admin:core_scheduledjobconfig_changelist')

    with patch('apps.core.admin.get_scheduler', return_value=None):
        response = admin_client.get(url)

    messages = [m.message for m in response.context['messages']]
    assert any('스케줄러가 비활성화' in m for m in messages)


@pytest.mark.django_db
def test_GitHub_잡은_interval_hours에_API_한도_안내가_노출된다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='fetch_github_activities', schedule_mode='interval', interval_hours=3,
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    response = admin_client.get(url)

    assert 'GitHub API 한도' in response.content.decode()


@pytest.mark.django_db
def test_GitHub_잡이_아니면_API_한도_안내가_노출되지_않는다(admin_client: Client) -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', schedule_mode='fixed_times', fixed_hours='8',
    )
    url = reverse('admin:core_scheduledjobconfig_change', args=[config.pk])

    response = admin_client.get(url)

    assert 'GitHub API 한도' not in response.content.decode()
