from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models

_ALLOWED_DISCORD_WEBHOOK_HOSTS = {'discord.com', 'discordapp.com', 'canary.discord.com', 'ptb.discord.com'}


def validate_discord_webhook_url(value: str) -> None:
    """Discord 웹훅 URL만 허용한다. Admin 전용 입력이라 실질 위험은 낮지만, 검증 없이 임의
    URL을 저장하면 서버가 그 URL로 POST 요청을 보내는 SSRF 벡터가 될 수 있어 저비용으로
    호스트·경로를 제한한다."""
    parsed = urlparse(value)
    if (
        parsed.scheme != 'https'
        or parsed.hostname not in _ALLOWED_DISCORD_WEBHOOK_HOSTS
        or not parsed.path.startswith('/api/webhooks/')
    ):
        raise ValidationError('Discord 웹훅 URL 형식이 아닙니다 (https://discord.com/api/webhooks/... 형태여야 합니다).')


CINEMA_SCREEN_CHOICES = [
    ('cgv_yongsan_imax', 'CGV 용산아이파크몰 IMAX'),
    ('lotte_jamsil_superplex', '롯데시네마 잠실 월드타워 수퍼플렉스'),
]


class NowShowingMovie(models.Model):
    """상영관별 '지금 상영 중' 영화 캐시 — sync_now_showing_movies가 채우며, Admin에서
    TrackedMovie를 등록할 때 드롭다운 소스로 쓰인다."""
    cinema_screen = models.CharField(max_length=30, choices=CINEMA_SCREEN_CHOICES, verbose_name='상영관')
    # CGV는 별도 영화 코드가 확인되지 않아 영화명(movNm) 원문을 그대로 저장한다(롯데는
    # RepresentationMovieCode) — CGV 쪽 값은 title과 동일한 문자열이 들어가므로 title보다
    # 짧게 잘리지 않도록 max_length를 title과 맞춘다.
    movie_code = models.CharField(max_length=200, verbose_name='영화 코드')
    title = models.CharField(max_length=200, verbose_name='제목')
    is_currently_showing = models.BooleanField(default=True, verbose_name='현재 상영 중')
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '지금 상영 중인 영화'
        verbose_name_plural = '지금 상영 중인 영화 목록'
        unique_together = ('cinema_screen', 'movie_code')

    def __str__(self) -> str:
        return f'[{self.get_cinema_screen_display()}] {self.title}'


class TrackedMovie(models.Model):
    """사용자가 등록한 감시 대상(영화 + 상영관)"""
    cinema_screen = models.CharField(max_length=30, choices=CINEMA_SCREEN_CHOICES, verbose_name='상영관')
    # 상영관에서 내려간(is_currently_showing=False) 영화도 감시 이력을 보존해야 하므로 PROTECT —
    # sync_now_showing_movies는 사라진 영화를 삭제하지 않고 플래그만 갱신한다.
    movie = models.ForeignKey(
        NowShowingMovie, on_delete=models.PROTECT, related_name='tracked_movies', verbose_name='영화',
    )
    is_active = models.BooleanField(default=True, verbose_name='감시 활성화')
    discord_webhook_url = models.URLField(
        verbose_name='Discord 웹훅 URL', validators=[validate_discord_webhook_url],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '영화 감시'
        verbose_name_plural = '영화 감시 목록'

    def __str__(self) -> str:
        return f'[{self.get_cinema_screen_display()}] {self.movie.title}'

    def save(self, *args: object, **kwargs: object) -> None:
        # cinema_screen은 NowShowingMovie.cinema_screen과 별도로 저장되는 값이라, Admin(고정된
        # 화면 + formfield_for_foreignkey로 스코프된 movie 선택지) 밖의 경로(쉘, 커맨드 등)로
        # 생성/수정하면 상영관이 다른 movie가 연결될 수 있다 — 저장 시점에 항상 일치를 강제한다.
        if self.movie_id and self.cinema_screen != self.movie.cinema_screen:
            raise ValueError(
                f'TrackedMovie.cinema_screen({self.cinema_screen})이 '
                f'movie.cinema_screen({self.movie.cinema_screen})과 일치하지 않습니다.',
            )
        super().save(*args, **kwargs)


class OpenedShowDate(models.Model):
    """감시 대상별로 발견된 오픈 날짜 이력 — 중복 알림 방지 겸 프런티어 계산의 기준.

    행 존재 자체는 "이 날짜가 열린 것을 발견했다"는 뜻이고, notify_succeeded가 실제 Discord
    발송 성공 여부다. 두 개념을 분리한 이유: Discord 발송이 실패했는데도 행을 만들고 끝내면
    (또는 애초에 행을 만들지 않고 재시도 판단 기준이 없으면) 다음 주기에 같은 날짜를 다시
    발견해도 재시도할 방법이 없어 알림이 영구히 유실된다 — apps.notifications.Notice가
    is_notified로 발송 성공 여부를 별도 추적하는 것과 같은 이유다.
    """
    tracked_movie = models.ForeignKey(
        TrackedMovie, on_delete=models.CASCADE, related_name='opened_dates', verbose_name='감시 대상',
    )
    show_date = models.DateField(verbose_name='상영일')
    showtimes = models.JSONField(default=list, verbose_name='상영 시간 목록')
    notify_succeeded = models.BooleanField(default=False, verbose_name='알림 발송 성공 여부')
    notified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '오픈된 상영일'
        verbose_name_plural = '오픈된 상영일 목록'
        unique_together = ('tracked_movie', 'show_date')

    def __str__(self) -> str:
        return f'{self.tracked_movie} — {self.show_date}'


class CinemaScreenWatchStatus(models.Model):
    """상영관 단위(최대 2행) 연속 크롤링 실패 카운터 — 실패 알림 안전장치."""
    cinema_screen = models.CharField(
        max_length=30, choices=CINEMA_SCREEN_CHOICES, unique=True, verbose_name='상영관',
    )
    consecutive_failure_count = models.PositiveSmallIntegerField(default=0, verbose_name='연속 실패 횟수')
    alert_sent = models.BooleanField(default=False, verbose_name='실패 알림 발송 여부')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '상영관 감시 상태'
        verbose_name_plural = '상영관 감시 상태 목록'

    def __str__(self) -> str:
        return self.get_cinema_screen_display()
