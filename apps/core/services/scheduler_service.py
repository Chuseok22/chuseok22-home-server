from apscheduler.triggers.cron import CronTrigger

from apps.core.models import ScheduledJobConfig
from apps.core.scheduler import SCHEDULER_TIMEZONE, get_scheduler


def update_job_schedule(job_id: str, is_enabled: bool, hour: int, minute: int) -> None:
    """자동화 잡 설정을 DB에 저장하고, 실행 중인 스케줄러가 있으면 즉시 반영한다."""
    config = ScheduledJobConfig.objects.get(job_id=job_id)
    config.is_enabled = is_enabled
    config.cron_hour = hour
    config.cron_minute = minute
    config.save()

    scheduler = get_scheduler()
    if scheduler is None:
        return  # ENABLE_SCHEDULER=False 환경 — DB만 갱신, 다음 기동 시 반영

    scheduler.reschedule_job(
        job_id,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=SCHEDULER_TIMEZONE),
    )
    if is_enabled:
        scheduler.resume_job(job_id)
    else:
        scheduler.pause_job(job_id)
