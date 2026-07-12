import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.core.models import ScheduledJobConfig


@pytest.mark.django_db
def test_ScheduledJobConfig_문자열_표현() -> None:
    config = ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    assert str(config) == 'check_new_notices'


@pytest.mark.django_db
def test_cron_hour_cron_minute_범위_초과시_full_clean에서_거부된다() -> None:
    """ScheduledJobConfigForm을 거치지 않는 경로(admin, shell 등) 대비 모델 레벨 방어선을 검증한다."""
    config = ScheduledJobConfig(job_id='check_new_notices', cron_hour=24, cron_minute=60)
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_job_id는_유일해야_한다() -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    with pytest.raises(IntegrityError):
        ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=9, cron_minute=0)


@pytest.mark.django_db
def test_cron_day_of_week_기본값은_매일이다() -> None:
    config = ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=8, cron_minute=0)
    assert config.cron_day_of_week == '*'


@pytest.mark.django_db
def test_cron_day_of_week에_유효하지_않은_값은_full_clean에서_거부된다() -> None:
    config = ScheduledJobConfig(
        job_id='check_new_notices', cron_hour=8, cron_minute=0, cron_day_of_week='invalid',
    )
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_schedule_mode_기본값은_fixed_times다() -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0, fixed_hours='8',
    )
    assert config.schedule_mode == 'fixed_times'


@pytest.mark.django_db
def test_interval_모드에서_interval_hours가_없으면_full_clean에서_거부된다() -> None:
    config = ScheduledJobConfig(
        job_id='check_new_notices', cron_hour=8, cron_minute=0, schedule_mode='interval',
    )
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_fixed_times_모드에서_fixed_hours가_비어있으면_full_clean에서_거부된다() -> None:
    config = ScheduledJobConfig(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        schedule_mode='fixed_times', fixed_hours='',
    )
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_fixed_hours에_0에서_23_범위를_벗어난_값이_있으면_거부된다() -> None:
    config = ScheduledJobConfig(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        schedule_mode='fixed_times', fixed_hours='3,24',
    )
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_interval_hours는_choices에_없는_값을_거부한다() -> None:
    config = ScheduledJobConfig(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        schedule_mode='interval', interval_hours=5,
    )
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_cron_day_of_week에_요일_콤보_저장이_가능하다() -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        fixed_hours='8', cron_day_of_week='mon,wed,fri',
    )
    config.full_clean()
    assert config.cron_day_of_week == 'mon,wed,fri'


@pytest.mark.django_db
def test_cron_day_of_week에_유효하지_않은_토큰이_섞여있으면_거부된다() -> None:
    config = ScheduledJobConfig(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        fixed_hours='8', cron_day_of_week='mon,invalid',
    )
    with pytest.raises(ValidationError):
        config.full_clean()
