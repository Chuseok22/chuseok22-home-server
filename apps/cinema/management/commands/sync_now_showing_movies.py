import logging

from django.core.management.base import BaseCommand

from apps.cinema.crawlers.base import BaseCinemaCrawler
from apps.cinema.crawlers.cgv import CgvYongsanImaxCrawler
from apps.cinema.crawlers.lotte import LotteJamsilSuperplexCrawler
from apps.cinema.models import NowShowingMovie

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '상영관별 "지금 상영 중" 영화 목록을 동기화한다 (Admin 감시 등록 드롭다운 소스)'

    # 테스트에서 patch.object(command, '_crawlers', {...})로 교체할 수 있도록 인스턴스 속성으로 둔다.
    _crawlers: dict[str, BaseCinemaCrawler] = {
        'cgv_yongsan_imax': CgvYongsanImaxCrawler(),
        'lotte_jamsil_superplex': LotteJamsilSuperplexCrawler(),
    }

    def handle(self, *args, **options) -> None:
        for cinema_screen, crawler in self._crawlers.items():
            self._sync_screen(cinema_screen, crawler)

    def _sync_screen(self, cinema_screen: str, crawler: BaseCinemaCrawler) -> None:
        try:
            movies = crawler.list_now_showing()
        except Exception as e:
            logger.error('[%s] 상영작 동기화 실패: %s', cinema_screen, e)
            self.stderr.write(f'[{cinema_screen}] 동기화 실패: {e}')
            return

        seen_codes = set()
        for movie in movies:
            seen_codes.add(movie.movie_code)
            NowShowingMovie.objects.update_or_create(
                cinema_screen=cinema_screen, movie_code=movie.movie_code,
                defaults={'title': movie.title, 'is_currently_showing': True},
            )
        NowShowingMovie.objects.filter(cinema_screen=cinema_screen).exclude(
            movie_code__in=seen_codes,
        ).update(is_currently_showing=False)
        self.stdout.write(f'[{cinema_screen}] {len(movies)}건 동기화 완료')
