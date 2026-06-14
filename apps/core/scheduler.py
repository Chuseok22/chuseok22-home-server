import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
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
    """30분마다 GitHub 활동 수집"""
    try:
        call_command('fetch_github_activities')
    except Exception as e:
        logger.error('fetch_github_activities 실행 실패: %s', e, exc_info=True)


def start_scheduler() -> None:
    """BackgroundScheduler를 생성하고 잡을 등록한 뒤 시작한다.

    고정 job id + replace_existing=True + 공유 DjangoJobStore 조합으로
    Gunicorn 멀티워커 환경에서도 잡이 DB상 단일 레코드로 수렴해 중복 실행을 방지한다.
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

    # 30분마다 GitHub 활동 수집
    scheduler.add_job(
        _run_fetch_github_activities,
        trigger=IntervalTrigger(minutes=30),
        id='fetch_github_activities',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info('APScheduler 시작됨 (timezone=%s)', _SCHEDULER_TIMEZONE)
