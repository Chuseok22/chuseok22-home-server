from django.core.exceptions import ValidationError
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

SCHEDULE_MODE_CHOICES = [
    ('interval', 'N시간마다'),
    ('fixed_times', '특정 시각'),
]

INTERVAL_HOURS_CHOICES = [(h, f'{h}시간마다') for h in (1, 2, 3, 4, 6, 8, 12, 24)]


class ScheduledJobConfig(models.Model):
    """자동화 잡(크롤링 등)의 활성화 여부·실행 스케줄을 저장한다.

    job_id는 apps/core/scheduler.py의 JOB_DEFINITIONS 키(APScheduler job id)와 일치해야 한다.
    schedule_mode에 따라 interval_* 또는 fixed_* 필드 그룹 중 하나만 유효하다.
    """

    job_id = models.CharField(max_length=100, unique=True)
    is_enabled = models.BooleanField(default=True)
    # ScheduledJobConfigForm이 폼 레벨에서 0-23/0-59를 이미 검증하지만,
    # 폼을 거치지 않는 향후 경로(admin 등록, shell 조작 등)에 대비한 모델 레벨 방어선.
    # default=0: 이 전환 기간 동안 cron_hour 없이(fixed_hours만으로) 새 행을 만들 수 있어야 하므로
    # (get_or_seed_job_config가 더 이상 cron_hour를 채우지 않음) 임시로 기본값을 둔다. Task 4에서 필드
    # 자체가 제거되므로 이 기본값은 그 전까지만 유효하다.
    cron_hour = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(23)])
    cron_minute = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])
    cron_day_of_week = models.CharField(max_length=3, choices=CRON_DAY_OF_WEEK_CHOICES, default='*')

    schedule_mode = models.CharField(max_length=20, choices=SCHEDULE_MODE_CHOICES, default='fixed_times')
    # interval 모드 전용 — schedule_mode='interval'일 때만 사용
    interval_hours = models.PositiveSmallIntegerField(choices=INTERVAL_HOURS_CHOICES, null=True, blank=True)
    interval_minute = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])
    # fixed_times 모드 전용 — schedule_mode='fixed_times'일 때만 사용. 콤마 구분 시(hour) 목록, 예: "3,9,15,21"
    fixed_hours = models.CharField(max_length=100, default='', blank=True)
    fixed_minute = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])

    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if self.schedule_mode == 'interval' and self.interval_hours is None:
            raise ValidationError({'interval_hours': 'interval 모드에서는 interval_hours가 필수입니다.'})
        if self.schedule_mode == 'fixed_times' and not self.fixed_hours:
            raise ValidationError({'fixed_hours': 'fixed_times 모드에서는 fixed_hours가 필수입니다.'})
        self._validate_fixed_hours()

    def _validate_fixed_hours(self) -> None:
        if not self.fixed_hours:
            return
        for token in self.fixed_hours.split(','):
            if not token.isdigit() or not (0 <= int(token) <= 23):
                raise ValidationError({'fixed_hours': f'"{token}"은 0~23 사이 정수가 아닙니다.'})

    def __str__(self) -> str:
        return self.job_id
