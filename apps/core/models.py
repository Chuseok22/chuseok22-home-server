from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

WEEKDAY_TOKENS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

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
    # 콤마 구분 요일 토큰 목록(예: "mon,wed,fri") 또는 전체 요일 시 "*"
    cron_day_of_week = models.CharField(max_length=30, default='*')

    # blank=True: Django admin의 기본 ModelForm이 이 필드들을 필수로 요구하지 않게 한다 — 실제
    # 모드별 필수 여부는 이미 clean()이 검증하므로 폼 레벨 필수 표시는 불필요하고, blank=True가
    # 없으면 기존 admin 테스트(POST 데이터에 이 필드들이 없는 케이스)가 폼 검증 단계에서 깨진다.
    schedule_mode = models.CharField(
        max_length=20, choices=SCHEDULE_MODE_CHOICES, default='fixed_times', blank=True,
    )
    # interval 모드 전용 — schedule_mode='interval'일 때만 사용
    interval_hours = models.PositiveSmallIntegerField(choices=INTERVAL_HOURS_CHOICES, null=True, blank=True)
    interval_minute = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])
    # fixed_times 모드 전용 — schedule_mode='fixed_times'일 때만 사용. 콤마 구분 시(hour) 목록, 예: "3,9,15,21"
    fixed_hours = models.CharField(max_length=100, default='', blank=True)
    fixed_minute = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])

    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        # 어드민 폼을 거치지 않고 생성/저장되는 경로(management command, 쉘 등)에 대한
        # 방어선 — schedule_mode가 두 유효값 밖이면 뒤 분기(interval/fixed_times)가 모두
        # 스킵되어 필수값 검증이 통째로 우회되므로 여기서 먼저 막는다.
        if self.schedule_mode not in ('interval', 'fixed_times'):
            raise ValidationError({'schedule_mode': 'schedule_mode는 interval 또는 fixed_times여야 합니다.'})
        if self.schedule_mode == 'interval' and self.interval_hours is None:
            raise ValidationError({'interval_hours': 'interval 모드에서는 interval_hours가 필수입니다.'})
        if self.schedule_mode == 'fixed_times' and not self.fixed_hours:
            # 이 메시지는 필드 키가 아니라 NON_FIELD_ERRORS로 발생시킨다 — fixed_hours는
            # apps/core/admin.py의 ScheduledJobConfigForm에서 항상 Meta.fields 밖으로
            # 제외되는 필드라서(실제 폼 필드로 존재한 적이 없음), 필드 키로 발생시키면
            # ModelForm._post_clean()의 instance.full_clean()이 이 에러를 잡은 뒤
            # Form.add_error(None, ...)로 넘길 때 "이 필드는 폼에 없다"는 이유로
            # ValueError를 던져 500이 난다(interval 모드에서 fixed_times로 전환하면서
            # 시각을 하나도 선택하지 않는 경로에서 실제로 재현됨). 필드 키 없이 발생시키면
            # NON_FIELD_ERRORS로 안전하게 처리된다.
            raise ValidationError('fixed_times 모드에서는 fixed_hours가 필수입니다.')
        self._validate_fixed_hours()
        self._validate_day_of_week()

    def _validate_fixed_hours(self) -> None:
        if not self.fixed_hours:
            return
        for token in self.fixed_hours.split(','):
            if not token.isdigit() or not (0 <= int(token) <= 23):
                # fixed_hours도 위와 동일하게 항상 폼 필드 밖이므로 필드 키 없이 발생시킨다.
                raise ValidationError(f'"{token}"은 0~23 사이 정수가 아닙니다.')

    def _validate_day_of_week(self) -> None:
        if self.cron_day_of_week == '*':
            return
        tokens = self.cron_day_of_week.split(',')
        if not tokens or any(token not in WEEKDAY_TOKENS for token in tokens):
            # cron_day_of_week도 위와 동일하게 항상 폼 필드 밖이므로 필드 키 없이 발생시킨다.
            raise ValidationError(
                'cron_day_of_week는 "*" 또는 유효 요일 토큰의 콤마 목록이어야 합니다.',
            )

    def __str__(self) -> str:
        return self.job_id
