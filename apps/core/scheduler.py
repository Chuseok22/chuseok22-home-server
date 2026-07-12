import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore

from apps.core.models import ScheduledJobConfig

logger = logging.getLogger(__name__)

SCHEDULER_TIMEZONE = 'Asia/Seoul'

# 자동화 잡 메타데이터. 새 자동화 잡을 추가할 때는 이 딕셔너리에만 등록하면
# 대시보드 자동화 제어 화면에 자동으로 노출된다.
JOB_DEFINITIONS = {
    'check_new_notices': {
        'label': '공지사항 크롤링',
        'command': 'check_new_notices',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '8',
        'default_fixed_minute': 0,
        'default_day_of_week': '*',
    },
    'fetch_github_activities': {
        'label': 'GitHub 활동 수집',
        'command': 'fetch_github_activities',
        'default_schedule_mode': 'interval',
        'default_interval_hours': 3,
        'default_interval_minute': 0,
        'default_day_of_week': '*',
    },
    'fetch_github_stats': {
        'label': 'GitHub 통계 수집 (잔디·star)',
        'command': 'fetch_github_stats',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '3',
        'default_fixed_minute': 5,
        'default_day_of_week': '*',
    },
    'cleanup_orphaned_media': {
        'label': '고아 이미지 파일 정리',
        'command': 'cleanup_orphaned_media',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '3',
        'default_fixed_minute': 0,
        'default_day_of_week': 'sun',
    },
}

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler | None:
    """실행 중인 스케줄러 인스턴스를 반환한다. 미기동 상태면 None."""
    return _scheduler


def get_or_seed_job_config(job_id: str, definition: dict) -> ScheduledJobConfig:
    """job_id에 대한 설정을 조회하고, 없으면 정의된 기본값으로 생성한다."""
    mode = definition['default_schedule_mode']
    defaults = {
        'schedule_mode': mode,
        'cron_day_of_week': definition['default_day_of_week'],
    }
    if mode == 'interval':
        defaults['interval_hours'] = definition['default_interval_hours']
        defaults['interval_minute'] = definition['default_interval_minute']
    else:
        defaults['fixed_hours'] = definition['default_fixed_hours']
        defaults['fixed_minute'] = definition['default_fixed_minute']

    config, _created = ScheduledJobConfig.objects.get_or_create(job_id=job_id, defaults=defaults)
    return config


def build_cron_trigger(config: ScheduledJobConfig) -> CronTrigger:
    """ScheduledJobConfig의 schedule_mode에 따라 APScheduler CronTrigger를 구성한다.

    interval 모드의 24시간은 cron 필드 문법상 '*/24'로 표현할 수 없다(APScheduler는 스텝 값이
    필드 범위(hour: 0~23, 즉 23)를 넘으면 ValueError를 던진다) — 하루 1회이므로 '매일 0시'와
    동일하게 hour='0'으로 변환한다.
    """
    if config.schedule_mode == 'interval':
        if config.interval_hours == 24:
            hour_expr: str | int = '0'
        else:
            hour_expr = f'*/{config.interval_hours}'
        minute_expr = config.interval_minute
    else:
        hour_expr = config.fixed_hours
        minute_expr = config.fixed_minute
    return CronTrigger(
        hour=hour_expr,
        minute=minute_expr,
        day_of_week=config.cron_day_of_week,
        timezone=SCHEDULER_TIMEZONE,
    )


def _run_job(command: str) -> None:
    try:
        call_command(command)
    except Exception as e:  # 잡 함수 예외가 스케줄러를 죽이지 않도록 방어
        logger.error('%s 실행 실패: %s', command, e, exc_info=True)


def start_scheduler() -> None:
    """BackgroundScheduler를 생성하고 JOB_DEFINITIONS의 잡을 DB 설정값으로 등록한 뒤 시작한다.

    DjangoJobStore로 잡 정의를 DB에 영속한다.
    중복 실행 방지는 다층으로 구성된다:
    - 프로세스 간: Gunicorn --workers 1 설정으로 단일 워커 보장
    - 프로세스 내: coalesce=True(동시 발동 압축), max_instances=1(동시 인스턴스 제한)
    """
    global _scheduler
    scheduler = BackgroundScheduler(timezone=SCHEDULER_TIMEZONE)
    scheduler.add_jobstore(DjangoJobStore(), 'default')
    _scheduler = scheduler

    for job_id, definition in JOB_DEFINITIONS.items():
        config = get_or_seed_job_config(job_id, definition)
        scheduler.add_job(
            _run_job,
            args=[definition['command']],
            trigger=build_cron_trigger(config),
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=300,
        )
        if not config.is_enabled:
            scheduler.pause_job(job_id)

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    logger.info('APScheduler 시작됨 (timezone=%s)', SCHEDULER_TIMEZONE)
