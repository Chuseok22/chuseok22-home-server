from apps.core.models import ScheduledJobConfig
from apps.core.scheduler import JOB_DEFINITIONS, build_cron_trigger, get_scheduler, run_job


def update_job_schedule(
    job_id: str,
    is_enabled: bool,
    schedule_mode: str,
    day_of_week: str,
    interval_hours: int | None = None,
    interval_minute: int = 0,
    interval_minutes: int | None = None,
    fixed_hours: str = '',
    fixed_minute: int = 0,
) -> None:
    """자동화 잡 설정을 DB에 저장하고, 실행 중인 스케줄러가 있으면 즉시 반영한다."""
    config = ScheduledJobConfig.objects.get(job_id=job_id)
    config.is_enabled = is_enabled
    config.schedule_mode = schedule_mode
    config.cron_day_of_week = day_of_week
    config.interval_hours = interval_hours
    config.interval_minute = interval_minute
    config.interval_minutes = interval_minutes
    config.fixed_hours = fixed_hours
    config.fixed_minute = fixed_minute
    config.save()

    scheduler = get_scheduler()
    if scheduler is None:
        return  # ENABLE_SCHEDULER=False 환경 — DB만 갱신, 다음 기동 시 반영

    scheduler.reschedule_job(job_id, trigger=build_cron_trigger(config))
    if is_enabled:
        scheduler.resume_job(job_id)
    else:
        scheduler.pause_job(job_id)


def run_job_now(job_id: str) -> tuple[bool, str]:
    """job_id에 해당하는 자동화 잡을 스케줄과 무관하게 즉시 1회 실행한다.

    실제 동시 실행 가드는 apps.core.scheduler.run_job()이 담당한다 — 스케줄러가 자동
    트리거한 실행과 여기서 즉시 실행하는 것이 모두 같은 함수를 거치므로 서로 겹치지
    않는다.
    """
    if job_id not in JOB_DEFINITIONS:
        return False, '정의되지 않은 작업입니다.'

    result = run_job(job_id)
    if result is None:
        return False, '이미 실행 중입니다.'
    if result:
        return True, '정상적으로 실행되었습니다.'
    return False, '실행 중 오류가 발생했습니다. 서버 로그를 확인해주세요.'
