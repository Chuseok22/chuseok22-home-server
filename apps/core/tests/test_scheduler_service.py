from unittest.mock import MagicMock, patch

import pytest

from apps.core.models import ScheduledJobConfig
from apps.core.services.scheduler_service import update_job_schedule


@pytest.mark.django_db
def test_스케줄러_미기동_상태에서는_DB만_갱신된다() -> None:
    ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0, fixed_hours='8',
    )

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=None):
        update_job_schedule(
            'check_new_notices', is_enabled=False, schedule_mode='fixed_times',
            day_of_week='mon', fixed_hours='10', fixed_minute=15,
        )

    config = ScheduledJobConfig.objects.get(job_id='check_new_notices')
    assert config.is_enabled is False
    assert config.fixed_hours == '10'
    assert config.fixed_minute == 15
    assert config.cron_day_of_week == 'mon'


@pytest.mark.django_db
def test_interval_모드로_저장하면_interval_필드가_반영된다() -> None:
    ScheduledJobConfig.objects.create(
        job_id='fetch_github_activities', cron_hour=3, cron_minute=0, fixed_hours='3',
    )

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=None):
        update_job_schedule(
            'fetch_github_activities', is_enabled=True, schedule_mode='interval',
            day_of_week='*', interval_hours=3, interval_minute=0,
        )

    config = ScheduledJobConfig.objects.get(job_id='fetch_github_activities')
    assert config.schedule_mode == 'interval'
    assert config.interval_hours == 3
    assert config.interval_minute == 0


@pytest.mark.django_db
def test_비활성화로_저장하면_reschedule_및_pause가_호출된다() -> None:
    ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0, fixed_hours='8',
    )
    mock_scheduler = MagicMock()

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=mock_scheduler):
        update_job_schedule(
            'check_new_notices', is_enabled=False, schedule_mode='fixed_times',
            day_of_week='*', fixed_hours='10', fixed_minute=15,
        )

    mock_scheduler.reschedule_job.assert_called_once()
    mock_scheduler.pause_job.assert_called_once_with('check_new_notices')
    mock_scheduler.resume_job.assert_not_called()


@pytest.mark.django_db
def test_활성화로_저장하면_resume이_호출된다() -> None:
    ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        fixed_hours='8', is_enabled=False,
    )
    mock_scheduler = MagicMock()

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=mock_scheduler):
        update_job_schedule(
            'check_new_notices', is_enabled=True, schedule_mode='fixed_times',
            day_of_week='*', fixed_hours='8', fixed_minute=0,
        )

    mock_scheduler.resume_job.assert_called_once_with('check_new_notices')
    mock_scheduler.pause_job.assert_not_called()
