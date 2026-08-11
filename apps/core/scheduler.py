import atexit
import logging
import threading

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
    'cleanup_old_github_activities': {
        'label': 'GitHub 활동 이력 정리',
        'command': 'cleanup_old_github_activities',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '4',
        'default_fixed_minute': 0,
        'default_day_of_week': '*',
    },
    'sync_kakao_favorites': {
        'label': '카카오맵 즐겨찾기 장소 동기화',
        'command': 'sync_kakao_favorites',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '5',
        'default_fixed_minute': 30,
        'default_day_of_week': 'sun',
    },
    'send_github_trending_report': {
        'label': 'GitHub 트렌딩 리포트',
        'command': 'send_github_trending_report',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '9',
        'default_fixed_minute': 0,
        'default_day_of_week': '*',
    },
    'check_movie_showtime_openings': {
        'label': '영화 예매 오픈 감지 (CGV/롯데)',
        'command': 'check_movie_showtime_openings',
        'default_schedule_mode': 'interval_minutes',
        'default_interval_minutes': 5,
        'default_day_of_week': '*',
    },
    'sync_now_showing_movies': {
        'label': '영화관 상영작 목록 동기화 (CGV/롯데)',
        'command': 'sync_now_showing_movies',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '6',
        'default_fixed_minute': 0,
        'default_day_of_week': '*',
    },
    'resync_movie_showtime_openings': {
        'label': '영화 예매 오픈 전체 재확인 (CGV/롯데)',
        'command': 'resync_movie_showtime_openings',
        'default_schedule_mode': 'fixed_times',
        'default_fixed_hours': '6',
        'default_fixed_minute': 30,
        'default_day_of_week': '*',
    },
}

_scheduler: BackgroundScheduler | None = None
_running_job_ids: set[str] = set()
_run_lock = threading.Lock()


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
    elif mode == 'interval_minutes':
        defaults['interval_minutes'] = definition['default_interval_minutes']
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
        minute_expr: str | int = config.interval_minute
    elif config.schedule_mode == 'interval_minutes':
        hour_expr = '*'
        minute_expr = f'*/{config.interval_minutes}'
    else:
        hour_expr = config.fixed_hours
        minute_expr = config.fixed_minute
    return CronTrigger(
        hour=hour_expr,
        minute=minute_expr,
        day_of_week=config.cron_day_of_week,
        timezone=SCHEDULER_TIMEZONE,
    )


def is_job_running(job_id: str) -> bool:
    """job_id가 현재 실행 중인지 확인한다."""
    with _run_lock:
        return job_id in _running_job_ids


def try_start_job(job_id: str) -> bool:
    """job_id 실행을 시도한다.

    이미 실행 중이면 False를 반환하고, 아니면 실행 중 상태로 표시한 뒤 True를 반환한다.
    """
    with _run_lock:
        if job_id in _running_job_ids:
            return False
        _running_job_ids.add(job_id)
        return True


def finish_job(job_id: str) -> None:
    """job_id의 실행 중 상태를 해제한다."""
    with _run_lock:
        _running_job_ids.discard(job_id)


def _run_job(command: str) -> bool:
    try:
        call_command(command)
        return True
    except Exception as e:  # 잡 함수 예외가 스케줄러를 죽이지 않도록 방어
        logger.error('%s 실행 실패: %s', command, e, exc_info=True)
        return False


def run_job(job_id: str) -> bool | None:
    """job_id에 해당하는 명령을 동시 실행 가드와 함께 실행한다.

    스케줄러의 자동 트리거(start_scheduler에서 등록)와 관리자의 즉시 실행
    (scheduler_service.run_job_now)이 모두 이 함수를 거친다 — 그래야 두 경로가
    같은 job_id에 대해 동시에 도는 것을 하나의 락으로 막을 수 있다. 이미 실행 중이면
    이번 요청은 조용히 건너뛴다(None 반환). job_id가 JOB_DEFINITIONS에 없는 경우(예:
    DjangoJobStore에 예전 job_id가 남아있는 등)를 대비해 방어적으로 처리한다 — 여기서
    KeyError를 그대로 던지면 APScheduler 백그라운드 스레드로 예외가 전파될 수 있다.
    """
    definition = JOB_DEFINITIONS.get(job_id)
    if definition is None:
        logger.error('JOB_DEFINITIONS에 등록되지 않은 job_id: %s', job_id)
        return False
    if not try_start_job(job_id):
        logger.info('%s 이(가) 이미 실행 중이라 이번 요청을 건너뜁니다', job_id)
        return None
    try:
        return _run_job(definition['command'])
    finally:
        finish_job(job_id)


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
            run_job,
            args=[job_id],
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
