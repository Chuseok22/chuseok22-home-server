import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

_SCHEDULER_TIMEZONE = 'Asia/Seoul'


def _run_check_new_notices() -> None:
    """매일 KST 08:00 공지·비교과 프로그램 크롤링"""
    try:
        call_command('check_new_notices')
    except Exception as e:  # 잡 함수 예외가 스케줄러를 죽이지 않도록 방어
        logger.error('check_new_notices 실행 실패: %s', e, exc_info=True)


def _run_fetch_github_activities() -> None:
    """매일 KST 03:00 GitHub 활동 수집"""
    try:
        call_command('fetch_github_activities')
    except Exception as e:
        logger.error('fetch_github_activities 실행 실패: %s', e, exc_info=True)


def start_scheduler() -> None:
    """BackgroundScheduler를 생성하고 잡을 등록한 뒤 시작한다.

    DjangoJobStore로 잡 정의를 DB에 영속한다.
    중복 실행 방지는 다층으로 구성된다:
    - 프로세스 간: Gunicorn --workers 1 설정으로 단일 워커 보장
    - 프로세스 내: coalesce=True(동시 발동 압축), max_instances=1(동시 인스턴스 제한)
    """
    scheduler = BackgroundScheduler(timezone=_SCHEDULER_TIMEZONE)
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    # 매일 KST 08:00 공지 크롤링
    scheduler.add_job(
        _run_check_new_notices,
        trigger=CronTrigger(hour=8, minute=0, timezone=_SCHEDULER_TIMEZONE),
        id='check_new_notices',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300,
    )

    # 매일 KST 03:00 GitHub 활동 수집
    scheduler.add_job(
        _run_fetch_github_activities,
        trigger=CronTrigger(hour=3, minute=0, timezone=_SCHEDULER_TIMEZONE),
        id='fetch_github_activities',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    logger.info('APScheduler 시작됨 (timezone=%s)', _SCHEDULER_TIMEZONE)
