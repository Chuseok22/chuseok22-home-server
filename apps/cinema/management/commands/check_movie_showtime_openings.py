from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cinema.crawlers.base import BaseCinemaCrawler
from apps.cinema.crawlers.cgv import CgvYongsanImaxCrawler
from apps.cinema.crawlers.lotte import LotteJamsilSuperplexCrawler
from apps.cinema.models import OpenedShowDate, TrackedMovie
from apps.cinema.services.discord import CinemaDiscordService
from apps.cinema.services.showtime_checker import run_showtime_check

_FRONTIER_BUFFER_DAYS = 3
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
    help = '감시 중인 영화의 새 예매 오픈 날짜를 프런티어 방식(오늘/다음 미확인일 기준 며칠)으로 확인한다'

    def handle(self, *args, **options) -> None:
        discord = CinemaDiscordService()
        for cinema_screen, crawler in _CRAWLERS.items():
            tracked_movies = list(
                TrackedMovie.objects.filter(
                    cinema_screen=cinema_screen, is_active=True, movie__is_currently_showing=True,
                ).select_related('movie'),
            )
            candidate_dates = self._build_candidate_dates(tracked_movies)
            notified_count = run_showtime_check(
                cinema_screen, crawler, candidate_dates, _SCREEN_LABELS[cinema_screen], discord,
            )
            self.stdout.write(f'[{cinema_screen}] 신규 알림 {notified_count}건')

    def _build_candidate_dates(self, tracked_movies: list[TrackedMovie]) -> list[date]:
        """감시 대상별로 '이미 알림 보낸 가장 늦은 날짜' 다음날부터 최대
        _FRONTIER_BUFFER_DAYS일치를 후보로 만든다. 여러 감시 대상의 후보 날짜를 합쳐
        중복 없이 정렬해 반환한다."""
        today = timezone.localdate()
        dates: set[date] = set()
        for tracked_movie in tracked_movies:
            opened_dates = OpenedShowDate.objects.filter(tracked_movie=tracked_movie)
            last_opened = opened_dates.filter(
                notify_succeeded=True,
            ).order_by('-show_date').values_list('show_date', flat=True).first()
            frontier_start = max(last_opened + timedelta(days=1), today) if last_opened else today
            for offset in range(_FRONTIER_BUFFER_DAYS):
                candidate = frontier_start + timedelta(days=offset)
                if (candidate - today).days <= _MAX_HORIZON_DAYS:
                    dates.add(candidate)
            # 한 크롤에서 여러 날짜가 한꺼번에 열렸을 때 앞쪽 날짜의 발송만 실패하고 뒤쪽
            # 날짜의 발송은 성공하면, 프런티어는 성공한(notify_succeeded=True) 뒤쪽 날짜
            # 기준으로 전진해 실패한 앞쪽 날짜가 다음 프런티어 버퍼에 들지 못하고 건너뛰어질
            # 수 있다 — 발송 실패(notify_succeeded=False)로 남은 날짜는 horizon 이내면
            # 프런티어 위치와 무관하게 항상 후보에 포함해 다음 5분 주기에 재시도되게 한다.
            failed_dates = opened_dates.filter(notify_succeeded=False).values_list('show_date', flat=True)
            for failed_date in failed_dates:
                if 0 <= (failed_date - today).days <= _MAX_HORIZON_DAYS:
                    dates.add(failed_date)
        return sorted(dates)
