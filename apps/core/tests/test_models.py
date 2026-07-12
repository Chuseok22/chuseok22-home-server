import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.core.models import ScheduledJobConfig
from apps.core.scheduler import JOB_DEFINITIONS, get_or_seed_job_config


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
def test_get_or_seed_job_config는_없으면_기본값으로_생성한다() -> None:
    definition = JOB_DEFINITIONS['check_new_notices']

    config = get_or_seed_job_config('check_new_notices', definition)

    assert config.cron_hour == definition['default_hour']
    assert config.cron_minute == definition['default_minute']
    assert config.is_enabled is True


@pytest.mark.django_db
def test_get_or_seed_job_config는_기존_값을_덮어쓰지_않는다() -> None:
    ScheduledJobConfig.objects.create(job_id='check_new_notices', cron_hour=23, cron_minute=59, is_enabled=False)
    definition = JOB_DEFINITIONS['check_new_notices']

    config = get_or_seed_job_config('check_new_notices', definition)

    assert config.cron_hour == 23
    assert config.cron_minute == 59
    assert config.is_enabled is False


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
def test_고아_미디어_정리_잡은_기본값이_일요일_새벽3시다() -> None:
    definition = JOB_DEFINITIONS['cleanup_orphaned_media']

    config = get_or_seed_job_config('cleanup_orphaned_media', definition)

    assert config.cron_hour == 3
    assert config.cron_minute == 0
    assert config.cron_day_of_week == 'sun'


@pytest.mark.django_db
def test_GitHub_통계_수집_잡은_기본값이_새벽_3시_5분이다() -> None:
    definition = JOB_DEFINITIONS['fetch_github_stats']

    config = get_or_seed_job_config('fetch_github_stats', definition)

    assert config.cron_hour == 3
    assert config.cron_minute == 5
    assert config.cron_day_of_week == '*'


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
