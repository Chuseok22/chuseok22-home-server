import pytest

from apps.core.models import ScheduledJobConfig
from apps.core.scheduler import JOB_DEFINITIONS, build_cron_trigger, get_or_seed_job_config


@pytest.mark.django_db
def test_get_or_seed_job_config는_interval_모드_기본값으로_생성한다() -> None:
    definition = JOB_DEFINITIONS['fetch_github_activities']

    config = get_or_seed_job_config('fetch_github_activities', definition)

    assert config.schedule_mode == 'interval'
    assert config.interval_hours == 3
    assert config.interval_minute == 0
    assert config.cron_day_of_week == '*'
    assert config.is_enabled is True


@pytest.mark.django_db
def test_get_or_seed_job_config는_fixed_times_모드_기본값으로_생성한다() -> None:
    definition = JOB_DEFINITIONS['check_new_notices']

    config = get_or_seed_job_config('check_new_notices', definition)

    assert config.schedule_mode == 'fixed_times'
    assert config.fixed_hours == '8'
    assert config.fixed_minute == 0


@pytest.mark.django_db
def test_get_or_seed_job_config는_기존_값을_덮어쓰지_않는다() -> None:
    ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        schedule_mode='fixed_times', fixed_hours='23', fixed_minute=59, is_enabled=False,
    )
    definition = JOB_DEFINITIONS['check_new_notices']

    config = get_or_seed_job_config('check_new_notices', definition)

    assert config.fixed_hours == '23'
    assert config.fixed_minute == 59
    assert config.is_enabled is False


@pytest.mark.django_db
def test_고아_미디어_정리_잡은_기본값이_일요일_새벽3시다() -> None:
    definition = JOB_DEFINITIONS['cleanup_orphaned_media']

    config = get_or_seed_job_config('cleanup_orphaned_media', definition)

    assert config.fixed_hours == '3'
    assert config.fixed_minute == 0
    assert config.cron_day_of_week == 'sun'


@pytest.mark.django_db
def test_GitHub_통계_수집_잡은_기본값이_새벽_3시_5분이다() -> None:
    definition = JOB_DEFINITIONS['fetch_github_stats']

    config = get_or_seed_job_config('fetch_github_stats', definition)

    assert config.fixed_hours == '3'
    assert config.fixed_minute == 5
    assert config.cron_day_of_week == '*'


@pytest.mark.django_db
def test_build_cron_trigger는_interval_모드에서_N시간마다_표현식을_만든다() -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='fetch_github_activities', cron_hour=3, cron_minute=0,
        schedule_mode='interval', interval_hours=3, interval_minute=0, cron_day_of_week='*',
    )

    trigger = build_cron_trigger(config)
    fields = {f.name: str(f) for f in trigger.fields}

    assert fields['hour'] == '*/3'
    assert fields['minute'] == '0'
    assert fields['day_of_week'] == '*'


@pytest.mark.django_db
def test_build_cron_trigger는_fixed_times_모드에서_시각_목록_표현식을_만든다() -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices', cron_hour=8, cron_minute=0,
        schedule_mode='fixed_times', fixed_hours='3,9,15,21', fixed_minute=0,
        cron_day_of_week='mon,wed,fri',
    )

    trigger = build_cron_trigger(config)
    fields = {f.name: str(f) for f in trigger.fields}

    assert fields['hour'] == '3,9,15,21'
    assert fields['minute'] == '0'
    assert fields['day_of_week'] == 'mon,wed,fri'


@pytest.mark.django_db
def test_build_cron_trigger는_interval_hours가_24면_매일_0시_표현식으로_변환한다() -> None:
    # APScheduler cron 필드는 스텝 값이 필드 범위(hour: 0~23)를 넘는 '*/24'를 허용하지 않는다.
    config = ScheduledJobConfig.objects.create(
        job_id='cleanup_orphaned_media', cron_hour=3, cron_minute=0,
        schedule_mode='interval', interval_hours=24, interval_minute=0, cron_day_of_week='*',
    )

    trigger = build_cron_trigger(config)
    fields = {f.name: str(f) for f in trigger.fields}

    assert fields['hour'] == '0'
