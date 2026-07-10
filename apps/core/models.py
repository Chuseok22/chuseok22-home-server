from django.core.validators import MaxValueValidator
from django.db import models

CRON_DAY_OF_WEEK_CHOICES = [
    ('*', '매일'),
    ('mon', '월요일'),
    ('tue', '화요일'),
    ('wed', '수요일'),
    ('thu', '목요일'),
    ('fri', '금요일'),
    ('sat', '토요일'),
    ('sun', '일요일'),
]


class ScheduledJobConfig(models.Model):
    """자동화 잡(크롤링 등)의 활성화 여부·실행 시각을 저장한다.

    job_id는 apps/core/scheduler.py의 JOB_DEFINITIONS 키(APScheduler job id)와 일치해야 한다.
    """

    job_id = models.CharField(max_length=100, unique=True)
    is_enabled = models.BooleanField(default=True)
    # ScheduledJobConfigForm이 폼 레벨에서 0-23/0-59를 이미 검증하지만,
    # 폼을 거치지 않는 향후 경로(admin 등록, shell 조작 등)에 대비한 모델 레벨 방어선.
    cron_hour = models.PositiveSmallIntegerField(validators=[MaxValueValidator(23)])
    cron_minute = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])
    cron_day_of_week = models.CharField(max_length=3, choices=CRON_DAY_OF_WEEK_CHOICES, default='*')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.job_id
