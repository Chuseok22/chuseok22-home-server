from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models

_ALLOWED_DISCORD_WEBHOOK_HOSTS = {'discord.com', 'discordapp.com', 'canary.discord.com', 'ptb.discord.com'}


def validate_discord_webhook_url(value: str) -> None:
    """Discord 웹훅 URL만 허용한다. Admin 전용 입력이라 실질 위험은 낮지만, 검증 없이 임의
    URL을 저장하면 서버가 그 URL로 POST 요청을 보내는 SSRF 벡터가 될 수 있어 저비용으로
    호스트·경로를 제한한다(apps.cinema.models의 동일 검증 로직을 앱 간 model import 없이 복제)."""
    parsed = urlparse(value)
    if (
        parsed.scheme != 'https'
        or parsed.hostname not in _ALLOWED_DISCORD_WEBHOOK_HOSTS
        or not parsed.path.startswith('/api/webhooks/')
    ):
        raise ValidationError('Discord 웹훅 URL 형식이 아닙니다 (https://discord.com/api/webhooks/... 형태여야 합니다).')


class TrackedClub(models.Model):
    """감시 대상 동아리 — name/homepage_url/discord_webhook_url만 채우면 새 동아리 추가가 끝난다.
    동아리별 전용 파싱 코드가 없으므로(로컬 LLM 기반 판별), 코드 변경 없이 확장 가능하다."""
    name = models.CharField(max_length=100, unique=True, verbose_name='동아리명')
    homepage_url = models.URLField(verbose_name='모집공고 페이지 URL')
    is_active = models.BooleanField(default=True, verbose_name='감시 활성화')
    discord_webhook_url = models.URLField(
        blank=True, default='', validators=[validate_discord_webhook_url], verbose_name='Discord 웹훅 URL',
    )
    is_recruiting_now = models.BooleanField(default=False, verbose_name='최근 확인 시 모집 중 여부')
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 확인 시각')
    consecutive_failure_count = models.PositiveSmallIntegerField(default=0, verbose_name='연속 실패 횟수')
    failure_alert_sent = models.BooleanField(default=False, verbose_name='실패 알림 발송 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록 시각')

    class Meta:
        verbose_name = '동아리 모집 감시'
        verbose_name_plural = '동아리 모집 감시 목록'

    def __str__(self) -> str:
        return self.name


class RecruitmentDetection(models.Model):
    """새로 감지된 모집 오픈 이력 — 알림 발송 로그 겸 dedupe 근거(상태 전이는
    TrackedClub.is_recruiting_now가 담당하고, 이 모델은 그 이력을 기록한다)."""
    tracked_club = models.ForeignKey(
        TrackedClub, on_delete=models.CASCADE, related_name='detections', verbose_name='감시 대상',
    )
    application_start = models.DateField(null=True, blank=True, verbose_name='지원 시작일')
    application_end = models.DateField(null=True, blank=True, verbose_name='지원 종료일')
    apply_url = models.URLField(blank=True, default='', verbose_name='지원 링크')
    evidence_quote = models.TextField(verbose_name='판별 근거 문장')
    notify_succeeded = models.BooleanField(default=False, verbose_name='알림 발송 성공 여부')
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name='감지 시각')

    class Meta:
        verbose_name = '모집 감지 이력'
        verbose_name_plural = '모집 감지 이력 목록'
        ordering = ('-detected_at',)

    def __str__(self) -> str:
        return f'{self.tracked_club} — {self.detected_at:%Y-%m-%d}'
