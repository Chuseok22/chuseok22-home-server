from unittest.mock import MagicMock, patch

import pytest

from apps.core.models import ScheduledJobConfig
from apps.core.services.scheduler_service import update_job_schedule


@pytest.mark.django_db
def test_스케줄러_미기동_상태에서는_DB만_갱신된다() -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=None):
        update_job_schedule('check_new_notices', is_enabled=False, hour=10, minute=15, day_of_week='mon')

    config = ScheduledJobConfig.objects.get(job_id='check_new_notices')
    assert config.is_enabled is False
    assert config.cron_hour == 10
    assert config.cron_minute == 15
    assert config.cron_day_of_week == 'mon'


@pytest.mark.django_db
def test_비활성화로_저장하면_reschedule_및_pause가_호출된다() -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    mock_scheduler = MagicMock()

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=mock_scheduler):
        update_job_schedule('check_new_notices', is_enabled=False, hour=10, minute=15, day_of_week='*')

    mock_scheduler.reschedule_job.assert_called_once()
    mock_scheduler.pause_job.assert_called_once_with('check_new_notices')
    mock_scheduler.resume_job.assert_not_called()


@pytest.mark.django_db
def test_활성화로_저장하면_resume이_호출된다() -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0, is_enabled=False)
    mock_scheduler = MagicMock()

    with patch('apps.core.services.scheduler_service.get_scheduler', return_value=mock_scheduler):
        update_job_schedule('check_new_notices', is_enabled=True, hour=8, minute=0, day_of_week='*')

    mock_scheduler.resume_job.assert_called_once_with('check_new_notices')
    mock_scheduler.pause_job.assert_not_called()
