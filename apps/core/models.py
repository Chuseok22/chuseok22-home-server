from django.db import models


class ScheduledJobConfig(models.Model):
    """자동화 잡(크롤링 등)의 활성화 여부·실행 시각을 저장한다.

    job_id는 apps/core/scheduler.py의 JOB_DEFINITIONS 키(APScheduler job id)와 일치해야 한다.
    """

    job_id = models.CharField(max_length=100, unique=True)
    is_enabled = models.BooleanField(default=True)
    cron_hour = models.PositiveSmallIntegerField()
    cron_minute = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.job_id
