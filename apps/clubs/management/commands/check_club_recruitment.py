import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clubs.models import RecruitmentDetection, TrackedClub
from apps.clubs.services.discord import ClubDiscordService
from apps.clubs.services.llm_recruitment_detector import RecruitmentResult, detect_recruitment
from apps.clubs.services.text_extractor import fetch_page_text

logger = logging.getLogger(__name__)

_FAILURE_ALERT_THRESHOLD = 5


class Command(BaseCommand):
    help = '감시 중인 동아리 홈페이지를 확인해 모집이 새로 열리면 Discord 알림을 발송한다'

    def handle(self, *args: object, **options: object) -> None:
        clubs = TrackedClub.objects.filter(is_active=True)
        if not clubs.exists():
            self.stdout.write('감시 중인 동아리가 없습니다.')
            return

        discord = ClubDiscordService()
        for club in clubs:
            if not club.discord_webhook_url:
                # 웹훅이 없으면 알림을 보낼 수 없으므로, fetch·LLM 호출까지 가는 파이프라인
                # 자체를 건너뛴다(apps.notifications.check_new_notices의 처리 방식과 동일) —
                # 웹훅을 채우기 전까지 매 주기 LLM을 호출하는 낭비를 막는다.
                logger.warning('[%s] discord_webhook_url 미설정 — 확인 자체를 건너뜀', club.name)
                self.stderr.write(f'[{club.name}] discord_webhook_url 미설정, 확인 건너뜀')
                continue
            self.stdout.write(f'[{club.name}] 확인 시작')
            self._process_club(club, discord)

    def _process_club(self, club: TrackedClub, discord: ClubDiscordService) -> None:
        # 실패 경고를 이미 보낸 뒤에도 매 주기 계속 확인한다 — 그래야 사이트가 복구됐을 때
        # _handle_success가 카운터와 failure_alert_sent를 초기화해 자동으로 정상 상태로 돌아온다.
        page_text = fetch_page_text(club.homepage_url)
        if page_text is None:
            self._handle_failure(club, discord)
            return

        result = detect_recruitment(club.name, page_text)
        if result is None:
            self._handle_failure(club, discord)
            return

        self._handle_success(club, discord, result)

    def _handle_failure(self, club: TrackedClub, discord: ClubDiscordService) -> None:
        club.consecutive_failure_count += 1
        club.last_checked_at = timezone.now()
        if club.consecutive_failure_count >= _FAILURE_ALERT_THRESHOLD and not club.failure_alert_sent:
            sent = discord.send_failure_alert(club.discord_webhook_url, club.name)
            club.failure_alert_sent = sent
            self.stderr.write(f'[{club.name}] 연속 {club.consecutive_failure_count}회 실패')
        club.save(update_fields=['consecutive_failure_count', 'failure_alert_sent', 'last_checked_at'])

    def _handle_success(self, club: TrackedClub, discord: ClubDiscordService, result: RecruitmentResult) -> None:
        club.consecutive_failure_count = 0
        club.failure_alert_sent = False
        club.last_checked_at = timezone.now()

        if not result.is_recruiting:
            club.is_recruiting_now = False
            club.save(update_fields=[
                'consecutive_failure_count', 'failure_alert_sent', 'last_checked_at', 'is_recruiting_now',
            ])
            self.stdout.write(f'[{club.name}] 모집 중 아님')
            return

        if club.is_recruiting_now:
            club.save(update_fields=['consecutive_failure_count', 'failure_alert_sent', 'last_checked_at'])
            self.stdout.write(f'[{club.name}] 이미 알림 발송된 모집 기간 — 건너뜀')
            return

        detection = RecruitmentDetection.objects.create(
            tracked_club=club,
            application_start=result.application_start,
            application_end=result.application_end,
            apply_url=result.apply_url,
            evidence_quote=result.evidence_quote,
        )
        success = discord.send_recruitment_alert(club.discord_webhook_url, club.name, detection)
        if success:
            detection.notify_succeeded = True
            detection.save(update_fields=['notify_succeeded'])
            club.is_recruiting_now = True
            self.stdout.write(f'[{club.name}] 신규 모집 알림 발송 완료')
        else:
            self.stderr.write(f'[{club.name}] 알림 발송 실패 — 다음 주기에 재시도')

        club.save(update_fields=[
            'consecutive_failure_count', 'failure_alert_sent', 'last_checked_at', 'is_recruiting_now',
        ])
