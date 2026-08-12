import json
import logging
from datetime import date, timedelta
from urllib.parse import quote

import requests
from django.utils import timezone

from .base import BaseCinemaCrawler, CinemaCrawlerError, NowShowingMovieItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://www.lottecinema.co.kr/LCWS/Ticketing/TicketingData.aspx'
_TICKETING_URL = 'https://www.lottecinema.co.kr/NLCHS/ticketing'
_CINEMA_ID = '1|0001|1016'  # 잠실 월드타워점
_SCREEN_DIVISION = '수퍼플렉스'
_REQUEST_TIMEOUT = 10
# list_now_showing은 상영작 "발견"용이라, 오늘 하루만 보면 아직 오늘 회차가 없고 며칠 뒤부터
# 개봉하는 영화(예: 개봉 예정작)를 놓칠 수 있다. check_movie_showtime_openings.py의
# _FRONTIER_BUFFER_DAYS와 동일한 3일 창을 두어, 그 버퍼 안에서 발견되지 않는 영화가 없게 한다.
_DISCOVERY_WINDOW_DAYS = 3
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
    구성했던 이전 구현보다 요청 수가 크게 줄었다(발견 시 41콜 → _DISCOVERY_WINDOW_DAYS(3)콜,
    확인 주기당 감시 영화 수 x 날짜 수 콜 → 날짜 수 콜). PlaySeqs.Items의 각 행이
    RepresentationMovieCode와 MovieNameKR을 함께 담고 있어, 상영작 발견에 별도로
    GetTicketingPageTOBE(전국 상영작 목록)를 쓸 필요도 없어졌다.

    - list_now_showing은 기준일 하루만 보면 아직 회차가 없는(며칠 뒤부터 개봉하는) 영화를
      놓칠 수 있어 _DISCOVERY_WINDOW_DAYS(3일) 창을 스캔한다 — 실제 상영일 발견은
      get_open_dates_bulk가 candidate_dates 전체를 다시 스캔하므로, 여기서는 감시 후보로
      "등록"할 영화를 놓치지 않는 것이 목적이다.
    - ScreenDivisionNameKR로 상영관 등급을 구분하며 "수퍼플렉스"(ScreenDivisionCode 940)가
      실제 값으로 확인되었다.
    - IsOK는 JSON boolean이 아니라 문자열("true")로 내려오는 것이 라이브 응답으로 확인됨 —
      다만 HAR에는 실패(false) 사례가 없어 문자열 "false" 표현은 추정이다. 둘 다 방어한다.
    - StartTime/EndTime은 CGV의 "HHMM"과 달리 이미 "HH:MM" 형식이라 별도 변환이 필요 없다.
    - build_booking_url이 반환하는 예매 화면 직행 URL(`NLCHS/ticketing?movieCd=...`)은 CGV와
      달리 URL 쿼리 파라미터만으로 영화 선택 상태를 재현한다 — 콜드 접속에도 동작함을 실측
      확인했다. 극장(cinemaID)까지 같은 방식으로 넘기는 파라미터는 HAR 캡처로도 발견하지
      못했다 — 예매 화면 내 극장 변경은 URL 파라미터가 아니라 별도 페이지 이동으로 처리되는
      것으로 보인다.
    """

    def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
        start_date = reference_date or timezone.localdate()
        seen: dict[str, NowShowingMovieItem] = {}
        for offset in range(_DISCOVERY_WINDOW_DAYS):
            target_date = start_date + timedelta(days=offset)
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

    def build_booking_url(self, movie_code: str, title: str) -> str:
        """예매 화면 직행 URL을 반환한다. 이 URL은 콜드 접속(새 탭에 직접 붙여넣기)에도 영화가
        이미 선택된 상태로 열리는 것을 실측 확인했다 — CGV와 달리 예매 화면 자체가 쿼리
        파라미터로 상태를 받는다."""
        return f'{_TICKETING_URL}?movieCd={movie_code}&movieName={quote(title)}'

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
        # PlaySeqs가 dict가 아니거나 Items가 list가 아니면 chained .get()/순회가 AttributeError나
        # TypeError를 내 CinemaCrawlerError로 감싸이지 않고 그대로 전파된다 — _call의 최상위
        # dict 검증만으로는 중첩 구조까지 보장되지 않아 여기서 한 번 더 검증한다.
        play_seqs = data.get('PlaySeqs')
        if not isinstance(play_seqs, dict):
            raise CinemaCrawlerError(f'롯데시네마 응답 형식이 예상과 다릅니다: PlaySeqs ({target_date})')
        items = play_seqs.get('Items')
        if not isinstance(items, list) or not all(isinstance(row, dict) for row in items):
            raise CinemaCrawlerError(f'롯데시네마 응답 형식이 예상과 다릅니다: PlaySeqs.Items ({target_date})')
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
            # CGV 크롤러의 _get과 동일한 이유로 response.json()도 try 안에서 호출한다 —
            # JSONDecodeError가 CinemaCrawlerError로 감싸이지 않으면 실패 카운터가 증가하지
            # 않고 handle() 루프가 중단될 수 있다.
            data = response.json()
            if not isinstance(data, dict):
                raise CinemaCrawlerError(f'롯데시네마 응답 형식이 예상과 다릅니다: {method_name}')
            return data
        except requests.RequestException as e:
            logger.error('롯데시네마 요청 실패 (method=%s): %s', method_name, type(e).__name__)
            raise CinemaCrawlerError(f'롯데시네마 요청 실패: {method_name}') from e
