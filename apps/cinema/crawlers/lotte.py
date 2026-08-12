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
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.lottecinema.co.kr/NLCHS/Ticketing',
}
# 실제 브라우저 요청(HAR 캡처)의 GetPlaySequence paramList에는 이 3개 필드가 항상 포함된다.
# 값 자체는 채널/OS 구분을 나타내는 범주형 상수라 개인 식별 정보가 아니다. 이 필드들 없이도
# 라이브 호출로 정상 동작을 확인했지만, 실제 트래픽과 최대한 가깝게 맞춰 서버 측의 예상치
# 못한 분기를 피한다. memberOnNo는 HAR상 GetTicketingPageTOBE 요청에만 있고 GetPlaySequence
# 요청에는 없어(직접 grep으로 재확인) 공통 파라미터에 포함하지 않는다 — GetPlaySequence만
# 쓰는 이 크롤러에는 필요 없다.
_COMMON_PARAMS = {
    'channelType': 'HO',
    'osType': 'W',
    'osVersion': _HEADERS['User-Agent'],
}


class LotteJamsilSuperplexCrawler(BaseCinemaCrawler):
    """롯데시네마 잠실 월드타워점 수퍼플렉스 상영 정보 크롤러

    엔드포인트·파라미터·필드 구성은 실제 브라우저 세션의 HAR 캡처로 라이브 검증되었다.

    GetPlaySequence(playDate, cinemaID, representationMovieCode)의 representationMovieCode를
    빈 문자열로 보내면 그 극장·날짜의 "모든 영화·모든 상영관" 회차를 한 번에 반환한다는 것이
    HAR로 확인됐다(실제 사이트도 페이지 최초 로드 시 이 방식으로 호출한다) — 영화별로 개별
    조회할 필요가 없어, 영화별 GetTicketingPageTOBE 조회 + 영화별 GetPlaySequence 조회로
    구성했던 이전 구현보다 요청 수가 크게 줄었다(발견 시 41콜 → 1콜, 확인 주기당 감시
    영화 수 × 날짜 수 콜 → 날짜 수 콜). PlaySeqs.Items의 각 행이 RepresentationMovieCode와
    MovieNameKR을 함께 담고 있어, 상영작 발견에 별도로 GetTicketingPageTOBE(전국 상영작 목록)를
    쓸 필요도 없어졌다.

    - ScreenDivisionNameKR로 상영관 등급을 구분하며 "수퍼플렉스"(ScreenDivisionCode 940)가
      실제 값으로 확인되었다.
    - IsOK는 JSON boolean이 아니라 문자열("true")로 내려오는 것이 라이브 응답으로 확인됨 —
      다만 HAR에는 실패(false) 사례가 없어 문자열 "false" 표현은 추정이다. 둘 다 방어한다.
    - StartTime/EndTime은 CGV의 "HHMM"과 달리 이미 "HH:MM" 형식이라 별도 변환이 필요 없다.
    """

    def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
        target_date = reference_date or timezone.localdate()
        seen: dict[str, NowShowingMovieItem] = {}
        for row in self._fetch_superplex_sessions_for_date(target_date):
            movie_code = str(row.get('RepresentationMovieCode', ''))
            title = row.get('MovieNameKR', '')
            if not movie_code or not title or movie_code in seen:
                continue
            seen[movie_code] = NowShowingMovieItem(movie_code=movie_code, title=title)
        return list(seen.values())

    def get_open_dates_bulk(
        self, movie_codes: list[str], candidate_dates: list[date],
    ) -> dict[str, dict[date, list[str]]]:
        result: dict[str, dict[date, list[str]]] = {code: {} for code in movie_codes}
        movie_code_set = set(movie_codes)
        for target_date in candidate_dates:
            for row in self._fetch_superplex_sessions_for_date(target_date):
                movie_code = str(row.get('RepresentationMovieCode', ''))
                if movie_code not in movie_code_set:
                    continue
                times = result[movie_code].setdefault(target_date, [])
                start_time = row.get('StartTime', '')
                if start_time not in times:
                    times.append(start_time)
        for movie_times in result.values():
            for times in movie_times.values():
                times.sort()
        return result

    def _fetch_superplex_sessions_for_date(self, target_date: date) -> list[dict]:
        """이 극장의 특정 날짜에 열려 있는 수퍼플렉스 회차 전체를 1콜로 가져온다."""
        data = self._call('GetPlaySequence', {
            'playDate': target_date.strftime('%Y-%m-%d'),
            'cinemaID': _CINEMA_ID,
            'representationMovieCode': '',
        })
        is_ok = data.get('IsOK')
        if is_ok is False or (isinstance(is_ok, str) and is_ok.lower() == 'false'):
            # IsOK=False(또는 문자열 "false")는 유효한 JSON dict이면서 애플리케이션 레벨로는
            # 실패한 응답이다 — 이 경우 PlaySeqs가 비어 있어 검증 없이 넘어가면 "회차 없음"과
            # 구분이 안 돼 run_showtime_check가 성공으로 기록하고 실패 카운터를 리셋해버린다.
            raise CinemaCrawlerError(
                f'롯데시네마 응답이 실패를 나타냅니다(IsOK={is_ok!r}): {target_date}',
            )
        items = data.get('PlaySeqs', {}).get('Items', [])
        return [row for row in items if row.get('ScreenDivisionNameKR') == _SCREEN_DIVISION]

    def _call(self, method_name: str, extra_params: dict) -> dict:
        param_list = {'MethodName': method_name, **_COMMON_PARAMS, **extra_params}
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
