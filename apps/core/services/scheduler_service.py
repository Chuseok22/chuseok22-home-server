from apps.core.models import ScheduledJobConfig
from apps.core.scheduler import build_cron_trigger, get_scheduler


def update_job_schedule(
    job_id: str,
    is_enabled: bool,
    schedule_mode: str,
    day_of_week: str,
    interval_hours: int | None = None,
    interval_minute: int = 0,
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
