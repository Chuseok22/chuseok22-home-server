from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cinema.crawlers.base import BaseCinemaCrawler
from apps.cinema.crawlers.cgv import CgvYongsanImaxCrawler
from apps.cinema.crawlers.lotte import LotteJamsilSuperplexCrawler
from apps.cinema.services.discord import CinemaDiscordService
from apps.cinema.services.showtime_checker import run_showtime_check

_MAX_HORIZON_DAYS = 14

_CRAWLERS: dict[str, BaseCinemaCrawler] = {
    'cgv_yongsan_imax': CgvYongsanImaxCrawler(),
    'lotte_jamsil_superplex': LotteJamsilSuperplexCrawler(),
}
_SCREEN_LABELS = {
    'cgv_yongsan_imax': 'CGV 용산아이파크몰 IMAX',
    'lotte_jamsil_superplex': '롯데시네마 잠실 월드타워 수퍼플렉스',
}


class Command(BaseCommand):
    help = (
        '감시 중인 영화의 0~14일 전체 상영일을 재확인한다 — 5분 간격 프런티어 체크(순서를 벗어나 '
        '열린 날짜 등)가 놓쳤을 수 있는 날짜를 하루 1회 보정한다'
    )

    def handle(self, *args, **options) -> None:
        discord = CinemaDiscordService()
        candidate_dates = self._build_candidate_dates()
        for cinema_screen, crawler in _CRAWLERS.items():
            notified_count = run_showtime_check(
                cinema_screen, crawler, candidate_dates, _SCREEN_LABELS[cinema_screen], discord,
            )
            self.stdout.write(f'[{cinema_screen}] 재확인 완료, 신규 알림 {notified_count}건')

    def _build_candidate_dates(self) -> list[date]:
        today = timezone.localdate()
        return [today + timedelta(days=offset) for offset in range(_MAX_HORIZON_DAYS + 1)]
