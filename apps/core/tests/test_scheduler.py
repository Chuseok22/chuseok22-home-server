from unittest.mock import MagicMock, patch

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
        job_id='check_new_notices',
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
def test_GitHub_활동_이력_정리_잡은_기본값이_매일_새벽4시다() -> None:
    definition = JOB_DEFINITIONS['cleanup_old_github_activities']

    config = get_or_seed_job_config('cleanup_old_github_activities', definition)

    assert config.fixed_hours == '4'
    assert config.fixed_minute == 0
    assert config.cron_day_of_week == '*'


@pytest.mark.django_db
def test_build_cron_trigger는_interval_모드에서_N시간마다_표현식을_만든다() -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='fetch_github_activities',
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
        job_id='check_new_notices',
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
        job_id='cleanup_orphaned_media',
        schedule_mode='interval', interval_hours=24, interval_minute=0, cron_day_of_week='*',
    )

    trigger = build_cron_trigger(config)
    fields = {f.name: str(f) for f in trigger.fields}

    assert fields['hour'] == '0'


@pytest.mark.django_db
def test_build_cron_trigger는_interval_minutes_모드에서_N분마다_표현식을_만든다() -> None:
    config = ScheduledJobConfig.objects.create(
        job_id='check_new_notices',
        schedule_mode='interval_minutes', interval_minutes=5, cron_day_of_week='*',
    )

    trigger = build_cron_trigger(config)
    fields = {f.name: str(f) for f in trigger.fields}

    assert fields['hour'] == '*'
    assert fields['minute'] == '*/5'
    assert fields['day_of_week'] == '*'


@pytest.mark.django_db
def test_카카오_즐겨찾기_동기화_잡은_기본값이_일요일_새벽_5시30분이다() -> None:
    definition = JOB_DEFINITIONS['sync_kakao_favorites']

    config = get_or_seed_job_config('sync_kakao_favorites', definition)

    assert config.schedule_mode == 'fixed_times'
    assert config.fixed_hours == '5'
    assert config.fixed_minute == 30
    assert config.cron_day_of_week == 'sun'


def test_try_start_job은_최초_호출_시_True를_반환하고_실행_중_상태가_된다() -> None:
    from apps.core.scheduler import finish_job, is_job_running, try_start_job

    assert is_job_running('check_new_notices') is False
    assert try_start_job('check_new_notices') is True
    assert is_job_running('check_new_notices') is True

    finish_job('check_new_notices')
    assert is_job_running('check_new_notices') is False


def test_try_start_job은_이미_실행_중이면_False를_반환한다() -> None:
    from apps.core.scheduler import try_start_job

    assert try_start_job('check_new_notices') is True
    assert try_start_job('check_new_notices') is False


def test__run_job은_성공하면_True를_반환한다() -> None:
    from apps.core.scheduler import _run_job

    with patch('apps.core.scheduler.call_command') as mock_call:
        result = _run_job('check_new_notices')

    mock_call.assert_called_once_with('check_new_notices')
    assert result is True


def test__run_job은_예외_발생_시_False를_반환한다() -> None:
    from apps.core.scheduler import _run_job

    with patch('apps.core.scheduler.call_command', side_effect=RuntimeError('boom')):
        result = _run_job('check_new_notices')

    assert result is False


def test_run_job은_성공하면_True를_반환한다() -> None:
    from apps.core.scheduler import run_job

    with patch('apps.core.scheduler.call_command') as mock_call:
        result = run_job('check_new_notices')

    mock_call.assert_called_once_with('check_new_notices')
    assert result is True


def test_run_job은_이미_실행_중이면_None을_반환하고_건너뛴다() -> None:
    """스케줄러 자동 트리거와 관리자 즉시 실행이 겹치는 상황을 재현한다 —
    둘 다 run_job()을 거치므로, 하나가 실행 중일 때 다른 하나는 실제로 command를
    실행하지 않고 조용히 건너뛰어야 한다."""
    from apps.core.scheduler import run_job, try_start_job

    try_start_job('check_new_notices')

    with patch('apps.core.scheduler.call_command') as mock_call:
        result = run_job('check_new_notices')

    mock_call.assert_not_called()
    assert result is None


def test_run_job은_예외_발생_시_False를_반환한다() -> None:
    from apps.core.scheduler import run_job

    with patch('apps.core.scheduler.call_command', side_effect=RuntimeError('boom')):
        result = run_job('check_new_notices')

    assert result is False


def test_run_job은_정의되지_않은_job_id면_예외_없이_False를_반환한다() -> None:
    """DjangoJobStore에 예전 job_id가 남아있는 등, JOB_DEFINITIONS에 없는 job_id로
    호출되어도 KeyError 없이 방어적으로 처리되어야 한다(APScheduler 스레드 보호)."""
    from apps.core.scheduler import run_job

    result = run_job('존재하지_않는_job')

    assert result is False


@pytest.mark.django_db
def test_start_scheduler는_각_잡을_동시_실행_락을_거치는_run_job으로_등록한다() -> None:
    """스케줄러 자동 트리거(add_job에 등록된 func)와 관리자 즉시 실행(run_job_now)이
    같은 동시 실행 방지 락을 공유하려면, add_job에 넘기는 func이 락을 거치는
    run_job이어야 한다(락을 거치지 않는 _run_job으로 되돌아가면 이 기능의 핵심
    불변조건이 깨진다). 실제 스케줄러 스레드가 뜨지 않도록 BackgroundScheduler와
    DjangoJobStore를 mock으로 대체한다."""
    from apps.core.scheduler import JOB_DEFINITIONS, run_job, start_scheduler

    mock_scheduler_instance = MagicMock()

    with patch('apps.core.scheduler.BackgroundScheduler', return_value=mock_scheduler_instance), \
            patch('apps.core.scheduler.DjangoJobStore'):
        start_scheduler()

    assert mock_scheduler_instance.add_job.call_count == len(JOB_DEFINITIONS)

    registered_job_ids = set()
    for call in mock_scheduler_instance.add_job.call_args_list:
        args, kwargs = call
        func = args[0] if args else kwargs.get('func')

        assert func is run_job
        assert kwargs['args'] == [kwargs['id']]

        registered_job_ids.add(kwargs['id'])

    assert registered_job_ids == set(JOB_DEFINITIONS.keys())


@pytest.mark.django_db
def test_GitHub_트렌딩_리포트_잡은_기본값이_매일_오전_9시다() -> None:
    definition = JOB_DEFINITIONS['send_github_trending_report']

    config = get_or_seed_job_config('send_github_trending_report', definition)

    assert definition['command'] == 'send_github_trending_report'
    assert config.schedule_mode == 'fixed_times'
    assert config.fixed_hours == '9'
    assert config.fixed_minute == 0
    assert config.cron_day_of_week == '*'
