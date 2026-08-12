from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


class CinemaCrawlerError(Exception):
    """영화관 API 요청/파싱 실패 시 발생한다."""


@dataclass(frozen=True)
class NowShowingMovieItem:
    """상영관에서 '지금 상영 중'으로 확인된 영화 1건 — NowShowingMovie 동기화에 사용된다."""
    movie_code: str
    title: str


class BaseCinemaCrawler(ABC):
    """CGV/롯데시네마 등 영화관 체인별 크롤러의 공통 인터페이스.

    체인별로 실제 상영 시간표를 배치 조회할 수 있는 단위가 다르다(둘 다 HAR 캡처로 검증됨).
    CGV는 영화 단위 엔드포인트(searchSiteScnscYmdListByMov)로 영화 하나당 "열린 날짜 목록"을
    한 번에 받아올 수 있어 movie_codes를 순회하며 날짜별 개별 조회를 줄인다. 롯데는 반대로
    날짜 단위 엔드포인트(GetPlaySequence, representationMovieCode='')로 그 날짜의 "모든 영화"
    회차를 한 번에 받아올 수 있어 candidate_dates만 순회한다. get_open_dates_bulk가 이 차이를
    각 구현체 내부로 숨겨, 호출자(management command)는 체인별 최적화를 몰라도 된다.
    """

    @abstractmethod
    def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
        """이 상영관에서 지금 상영 중인 영화 목록을 반환한다."""

    @abstractmethod
    def get_open_dates_bulk(
        self, movie_codes: list[str], candidate_dates: list[date],
    ) -> dict[str, dict[date, list[str]]]:
        """movie_codes 각각에 대해, candidate_dates 중 실제로 상영 회차가 열려 있는 날짜만
        {movie_code: {show_date: [showtime_str, ...]}} 형태로 반환한다. 열려 있지 않은 날짜는
        결과에 아예 포함되지 않는다(빈 리스트가 아니라 키 자체가 없음)."""
