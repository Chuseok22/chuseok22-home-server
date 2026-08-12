import logging
from datetime import date

import requests
from django.utils import timezone

from .base import BaseCinemaCrawler, CinemaCrawlerError, NowShowingMovieItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://cgv.co.kr/api/v1/booking/searchMovScnInfo'
_SITE_NO = '0013'  # 용산아이파크몰
_CO_CD = 'A420'
_RTCTL_SCOP_CD = '08'
_SCREEN_KEYWORD = 'imax'
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://cgv.co.kr/cnm/movieBook/cinema',
}


class CgvYongsanImaxCrawler(BaseCinemaCrawler):
    """CGV 용산아이파크몰 IMAX 상영 정보 크롤러

    응답 필드명(movNm, scnsNm, scnsrtTm, scnendTm 등)과 scnsrtTm/scnendTm의 "HHMM" 포맷은
    참고 오픈소스 구현(Heechan93/argos-cgv-imax)의 소스 코드를 읽어 확인한 것으로, 리서치
    환경에서 매 요청이 403으로 막혀 실제 raw 응답 바디로 직접 검증하지는 못했다. movNo(안정
    영화 식별자) 필드는 별도의 두 독립 공개 문서(hmmhmmhm/daiso-mcp, NomaDamas/k-skill)가
    이 엔드포인트 응답에 포함된다고 기록하고 있어 우선 사용하되, 실제로 없을 경우를 대비해
    영화명(movNm) 폴백을 유지한다. 배포 후 홈서버에서 sync_now_showing_movies를 1회 수동
    실행해 실제 필드 구성(movNo 존재 여부 포함)을 확인해야 한다.
    """

    def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
        target_date = reference_date or timezone.localdate()
        rows = self._fetch(target_date)
        seen: dict[str, NowShowingMovieItem] = {}
        for row in rows:
            if not self._is_imax_row(row):
                continue
            title = row.get('movNm', '')
            if not title:
                continue
            movie_code = self._extract_movie_code(row, title)
            if movie_code in seen:
                continue
            seen[movie_code] = NowShowingMovieItem(movie_code=movie_code, title=title)
        return list(seen.values())

    def get_open_dates_bulk(
        self, movie_codes: list[str], candidate_dates: list[date],
    ) -> dict[str, dict[date, list[str]]]:
        result: dict[str, dict[date, list[str]]] = {code: {} for code in movie_codes}
        movie_code_set = set(movie_codes)
        for target_date in candidate_dates:
            rows = self._fetch(target_date)
            for row in rows:
                if not self._is_imax_row(row):
                    continue
                movie_code = self._extract_movie_code(row, row.get('movNm', ''))
                if movie_code not in movie_code_set:
                    continue
                showtime = self._format_time(row.get('scnsrtTm', ''))
                times = result[movie_code].setdefault(target_date, [])
                if showtime not in times:
                    times.append(showtime)
        for movie_times in result.values():
            for times in movie_times.values():
                times.sort()
        return result

    def _extract_movie_code(self, row: dict, title: str) -> str:
        """movNo(제목과 독립적인 안정 식별자)가 있으면 우선 사용하고, 없으면 영화명(movNm)
        으로 폴백한다 — movNo가 이 엔드포인트 응답에 실제로 포함되는지는 raw 응답으로
        검증하지 못했으므로(클래스 docstring 참고) 폴백을 유지한다. movNo를 쓰면 재개봉·
        리마스터 등으로 제목 표기가 바뀌어도 감시 대상이 끊기지 않는다."""
        movie_code = row.get('movNo')
        if movie_code:
            return str(movie_code)
        return title

    def _fetch(self, target_date: date) -> list[dict]:
        params = {
            'coCd': _CO_CD,
            'siteNo': _SITE_NO,
            'scnYmd': target_date.strftime('%Y%m%d'),
            'rtctlScopCd': _RTCTL_SCOP_CD,
        }
        try:
            response = requests.get(_BASE_URL, params=params, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            # WAF 차단 시 HTTP 200과 함께 JSON이 아닌 HTML 차단 페이지가 올 수 있다 —
            # response.json()을 try 밖에서 호출하면 이 경우 CinemaCrawlerError로 감싸이지 않고
            # 그대로 전파되어, run_showtime_check의 실패 카운터가 증가하지 않고(실패 알림
            # 안전장치 무력화) check_movie_showtime_openings의 다음 상영관(롯데) 처리까지
            # 중단시킬 수 있다. requests의 JSONDecodeError는 RequestException의 서브클래스라
            # 아래 except가 그대로 잡는다.
            rows = response.json().get('data')
            if not isinstance(rows, list):
                raise CinemaCrawlerError(f'CGV 응답 형식이 예상과 다릅니다: {target_date}')
            return rows
        except requests.RequestException as e:
            logger.error('CGV 상영 정보 요청 실패 (date=%s): %s', target_date, type(e).__name__)
            raise CinemaCrawlerError(f'CGV 요청 실패: {target_date}') from e

    def _is_imax_row(self, row: dict) -> bool:
        return _SCREEN_KEYWORD in row.get('scnsNm', '').lower()

    def _format_time(self, raw: str) -> str:
        """"HHMM" 4자리 문자열을 "HH:MM"으로 변환한다. 예상과 다른 형식이면 원문을 그대로 둔다."""
        if len(raw) != 4 or not raw.isdigit():
            return raw
        return f'{raw[:2]}:{raw[2:]}'
