import json
import logging
from datetime import date

import requests
from django.utils import timezone

from .base import BaseCinemaCrawler, CinemaCrawlerError, NowShowingMovieItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://www.lottecinema.co.kr/LCWS/Ticketing/TicketingData.aspx'
_CINEMA_ID = '1|0001|1016'  # 잠실 월드타워점
_SCREEN_DIVISION = '수퍼플렉스'
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ),
}


class LotteJamsilSuperplexCrawler(BaseCinemaCrawler):
    """롯데시네마 잠실 월드타워점 수퍼플렉스 상영 정보 크롤러"""

    def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
        target_date = reference_date or timezone.localdate()
        data = self._call('GetTicketingPageTOBE', {})
        movies = data.get('Movies', {}).get('Movies', {}).get('Items', [])

        result: list[NowShowingMovieItem] = []
        for movie in movies:
            movie_code = str(movie.get('RepresentationMovieCode', ''))
            title = movie.get('MovieNameKR', '')
            if not movie_code or not title:
                continue
            if self._fetch_superplex_sessions(movie_code, target_date):
                result.append(NowShowingMovieItem(movie_code=movie_code, title=title))
        return result

    def get_open_dates_bulk(
        self, movie_codes: list[str], candidate_dates: list[date],
    ) -> dict[str, dict[date, list[str]]]:
        result: dict[str, dict[date, list[str]]] = {code: {} for code in movie_codes}
        for movie_code in movie_codes:
            for target_date in candidate_dates:
                sessions = self._fetch_superplex_sessions(movie_code, target_date)
                if not sessions:
                    continue
                times = sorted({row.get('StartTime', '') for row in sessions})
                result[movie_code][target_date] = times
        return result

    def _fetch_superplex_sessions(self, movie_code: str, target_date: date) -> list[dict]:
        data = self._call('GetPlaySequence', {
            'playDate': target_date.strftime('%Y-%m-%d'),
            'cinemaID': _CINEMA_ID,
            'representationMovieCode': movie_code,
        })
        is_ok = data.get('IsOK')
        if is_ok is False or (isinstance(is_ok, str) and is_ok.lower() == 'false'):
            # IsOK=False는 유효한 JSON dict이면서 애플리케이션 레벨로는 실패한 응답이다 —
            # 이 경우 PlaySeqs가 비어 있어 검증 없이 넘어가면 "회차 없음"과 구분이 안 돼
            # run_showtime_check가 성공으로 기록하고 실패 카운터를 리셋해버린다. 이 응답도
            # raw로 검증하지 못했으므로 boolean false 외에 문자열 "false"로 내려올 가능성도
            # 함께 방어한다.
            raise CinemaCrawlerError(
                f'롯데시네마 응답이 실패를 나타냅니다(IsOK={is_ok!r}): {movie_code} {target_date}',
            )
        items = data.get('PlaySeqs', {}).get('Items', [])
        return [row for row in items if row.get('ScreenDivisionNameKR') == _SCREEN_DIVISION]

    def _call(self, method_name: str, extra_params: dict) -> dict:
        param_list = {'MethodName': method_name, **extra_params}
        try:
            response = requests.post(
                _BASE_URL,
                files={'paramList': (None, json.dumps(param_list))},
                headers=_HEADERS,
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            # CGV 크롤러의 _fetch와 동일한 이유로 response.json()도 try 안에서 호출한다 —
            # JSONDecodeError가 CinemaCrawlerError로 감싸이지 않으면 실패 카운터가 증가하지
            # 않고 handle() 루프가 중단될 수 있다.
            data = response.json()
            if not isinstance(data, dict):
                raise CinemaCrawlerError(f'롯데시네마 응답 형식이 예상과 다릅니다: {method_name}')
            return data
        except requests.RequestException as e:
            logger.error('롯데시네마 요청 실패 (method=%s): %s', method_name, type(e).__name__)
            raise CinemaCrawlerError(f'롯데시네마 요청 실패: {method_name}') from e
