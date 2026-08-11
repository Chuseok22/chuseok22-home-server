import logging
from datetime import date

from apps.cinema.crawlers.base import BaseCinemaCrawler
from apps.cinema.models import CinemaScreenWatchStatus, OpenedShowDate, TrackedMovie
from apps.cinema.services.discord import CinemaDiscordService

logger = logging.getLogger(__name__)

_FAILURE_THRESHOLD = 5


def run_showtime_check(
    cinema_screen: str,
    crawler: BaseCinemaCrawler,
    candidate_dates: list[date],
    cinema_screen_label: str,
    booking_url: str,
    discord: CinemaDiscordService,
) -> int:
    """cinema_screen에서 활성 감시 대상의 candidate_dates 중 새로 열린 날짜를 찾아 알림을
    보낸다. 새로 알림을 보낸 날짜 수를 반환한다."""
    tracked_movies = list(
        TrackedMovie.objects.filter(
            cinema_screen=cinema_screen, is_active=True, movie__is_currently_showing=True,
        ).select_related('movie'),
    )
    if not tracked_movies or not candidate_dates:
        return 0

    movie_codes = [tm.movie.movie_code for tm in tracked_movies]
    try:
        open_dates = crawler.get_open_dates_bulk(movie_codes, candidate_dates)
    except Exception as e:
        # CinemaCrawlerError뿐 아니라 크롤러 내부에서 예상 못 한 예외(AttributeError 등)가
        # 나도 실패 카운터를 증가시켜야 한다 — 좁은 except로 두면 이런 예외가 그대로
        # 전파되어 handle() 루프가 다른 상영관 체크까지 중단시킨다.
        logger.error('[%s] 크롤링 실패: %s: %s', cinema_screen, type(e).__name__, e)
        _record_failure(cinema_screen, cinema_screen_label, tracked_movies, discord)
        return 0

    _record_success(cinema_screen)

    notified_count = 0
    for tracked_movie in tracked_movies:
        movie_code = tracked_movie.movie.movie_code
        for show_date, showtimes in open_dates.get(movie_code, {}).items():
            if _notify_if_new(tracked_movie, show_date, showtimes, cinema_screen_label, booking_url, discord):
                notified_count += 1
    return notified_count


def _notify_if_new(
    tracked_movie: TrackedMovie,
    show_date: date,
    showtimes: list[str],
    cinema_screen_label: str,
    booking_url: str,
    discord: CinemaDiscordService,
) -> bool:
    # 행 존재(발견 여부)와 notify_succeeded(발송 성공 여부)를 분리한다 — Discord 발송이
    # 실패해도 행은 만들어지지만 notify_succeeded=False로 남아, 다음 체크 주기(프런티어 또는
    # 전체 재확인)가 같은 날짜를 다시 candidate_dates에 넣었을 때 재시도된다.
    opened, _created = OpenedShowDate.objects.get_or_create(
        tracked_movie=tracked_movie, show_date=show_date, defaults={'showtimes': showtimes},
    )
    if opened.notify_succeeded:
        return False
    success = discord.send_new_date_alert(
        webhook_url=tracked_movie.discord_webhook_url,
        cinema_screen_label=cinema_screen_label,
        movie_title=tracked_movie.movie.title,
        show_date=show_date,
        showtimes=showtimes,
        booking_url=booking_url,
    )
    if success:
        opened.notify_succeeded = True
        opened.showtimes = showtimes
        opened.save(update_fields=['notify_succeeded', 'showtimes'])
    return success


def _record_failure(
    cinema_screen: str, cinema_screen_label: str, tracked_movies: list[TrackedMovie],
    discord: CinemaDiscordService,
) -> None:
    status, _created = CinemaScreenWatchStatus.objects.get_or_create(cinema_screen=cinema_screen)
    # PositiveSmallIntegerField는 32767이 상한이다 — alert_sent=True 이후에는 실질적으로
    # 무의미한 값이 계속 증가하는 것을 막기 위해 임계치 이후로는 더 늘리지 않는다.
    if status.consecutive_failure_count < _FAILURE_THRESHOLD:
        status.consecutive_failure_count += 1
    if status.consecutive_failure_count >= _FAILURE_THRESHOLD and not status.alert_sent:
        webhook_urls = sorted({tm.discord_webhook_url for tm in tracked_movies})
        discord.send_failure_alert(webhook_urls, cinema_screen_label)
        status.alert_sent = True
    status.save()


def _record_success(cinema_screen: str) -> None:
    CinemaScreenWatchStatus.objects.update_or_create(
        cinema_screen=cinema_screen, defaults={'consecutive_failure_count': 0, 'alert_sent': False},
    )
