import logging
from datetime import date, datetime

import requests

from .base import BaseCinemaCrawler, CinemaCrawlerError, NowShowingMovieItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://cgv.co.kr/api/v1/booking'
_SITE_NO = '0013'  # 용산아이파크몰
_CO_CD = 'A420'
_RTCTL_SCOP_CD = '08'
_IMAX_SCREEN_KEYWORD = 'imax'
# searchSscnsSchdCntList 응답에는 comCd(코드 그룹)별로 "03"이 서로 다른 의미로 중복 등장한다
# — TCSCNS_GRAD_CD의 03은 "아이맥스"이지만 SASCNS_GRAD_CD의 03은 "골드클래스"다. comCd를
# 함께 확인하지 않으면 응답 내 그룹 순서에 따라 골드클래스를 IMAX로 오판할 수 있다(HAR로 실제
# 확인됨).
_IMAX_FORMAT_GROUP = 'TCSCNS_GRAD_CD'
_IMAX_FORMAT_CODE = '03'
# searchSscnsSchdCntList는 위치 좌표를 요구하지만 결과의 사이트 "정렬 순서"에만 쓰이고,
# 우리가 실제로 쓰는 값(IMAX 그룹의 사이트 코드 목록 자체)에는 영향을 주지 않는다(라이브
# 호출로 확인됨) — 서울시청 좌표처럼 특정 개인과 무관한 공개 참조점을 쓴다. 최초 구현 때는
# HAR 캡처 세션의 실제 좌표를 그대로 썼는데, 이는 캡처 당시 사용자 기기의 실제 위치(위치정보
# API 값으로 추정)라 개인 식별 정보가 소스코드에 남는 문제가 있어 교체했다.
_LOCATION = {'lttd': '37.5665', 'lntd': '126.9780'}
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
    'Accept-Language': 'ko-KR',
    'Referer': 'https://cgv.co.kr/cnm/movieBook/movie',
}


class CgvYongsanImaxCrawler(BaseCinemaCrawler):
    """CGV 용산아이파크몰 IMAX 상영 정보 크롤러

    아래 4개 엔드포인트와 필드 구성(movNo, scnsNm, siteNo, scnsrtTm 등)은 실제 브라우저
    세션의 HAR 캡처로 라이브 검증되었다 — 과거 리서치 중 추정했던 searchMovScnInfo 엔드포인트는
    실제로 브라우저가 사용하지 않는 것으로 확인되어 폐기했다. 쿠키/로그인 없이도(요청에 커스텀
    인증 헤더·custNo 없이) 전부 200으로 응답하는 것을 라이브 호출로 확인했다:

    - searchAtktTopPostrList(coCd): 전국 "지금 예매 가능한" 영화 목록(movNo, movNm). 특정
      상영관에 한정되지 않는다 — 발견용 후보 목록으로만 쓴다.
    - searchSscnsSchdCntList(coCd, movNo, lntd, lttd): 영화 하나가 상영관 등급
      (comCd=TCSCNS_GRAD_CD)별로 어느 사이트(siteNo)에서 상영되는지 반환한다. IMAX 코드(03)
      항목의 사이트 목록에 siteNo가 포함되는지로 "이 영화가 이 상영관 IMAX에서 상영 중인지"
      판정한다 — comCdval만으로는 다른 코드 그룹(SASCNS_GRAD_CD)의 "03"(골드클래스)과
      혼동될 수 있어 comCd까지 함께 확인한다.
    - searchSiteScnscYmdListByMov(coCd, siteNo, movNo): 영화+상영관 기준으로 열려 있는 상영일
      목록을 한 번에 반환한다(날짜별 개별 조회 불필요) — 롯데에는 없는, CGV만의 이점이다.
    - searchSchByMov(coCd, siteNo, scnYmd, movNo, rtctlScopCd): 영화+상영관+날짜의 실제
      회차(시간)를 반환한다. siteNo로 요청해도 인접한 다른 브랜드관(예: 씨네드쉐프)
      회차가 함께 섞여 나오는 것이 확인되어, 응답의 siteNo 필드로 다시 한번 걸러야 한다.
    """

    def list_now_showing(self, reference_date: date | None = None) -> list[NowShowingMovieItem]:
        result: list[NowShowingMovieItem] = []
        for movie in self._fetch_top_movies():
            movie_no = str(movie.get('movNo', ''))
            title = movie.get('movNm', '')
            if not movie_no or not title:
                continue
            if self._plays_in_imax_at_site(movie_no):
                result.append(NowShowingMovieItem(movie_code=movie_no, title=title))
        return result

    def get_open_dates_bulk(
        self, movie_codes: list[str], candidate_dates: list[date],
    ) -> dict[str, dict[date, list[str]]]:
        result: dict[str, dict[date, list[str]]] = {code: {} for code in movie_codes}
        candidate_set = set(candidate_dates)
        for movie_code in movie_codes:
            open_dates = [d for d in self._fetch_open_dates(movie_code) if d in candidate_set]
            for target_date in open_dates:
                rows = self._fetch_schedule(movie_code, target_date)
                times = sorted({
                    self._format_time(row.get('scnsrtTm', '')) for row in rows if self._is_imax_row(row)
                })
                if times:
                    result[movie_code][target_date] = times
        return result

    def _plays_in_imax_at_site(self, movie_no: str) -> bool:
        for entry in self._fetch_schedule_count(movie_no):
            if entry.get('comCd') != _IMAX_FORMAT_GROUP or entry.get('comCdval') != _IMAX_FORMAT_CODE:
                continue
            sites = [site.get('siteNo') for site in entry.get('sscnsSiteList', [])]
            return _SITE_NO in sites
        return False

    def _fetch_top_movies(self) -> list[dict]:
        params = {'coCd': _CO_CD, 'movNm': '', 'div': '', 'attrCd': ''}
        return self._get(f'{_BASE_URL}/searchAtktTopPostrList', params)

    def _fetch_schedule_count(self, movie_no: str) -> list[dict]:
        params = {'coCd': _CO_CD, 'movNo': movie_no, **_LOCATION}
        return self._get(f'{_BASE_URL}/searchSscnsSchdCntList', params)

    def _fetch_open_dates(self, movie_no: str) -> list[date]:
        params = {'coCd': _CO_CD, 'siteNo': _SITE_NO, 'movNo': movie_no}
        rows = self._get(f'{_BASE_URL}/searchSiteScnscYmdListByMov', params)
        dates: list[date] = []
        for row in rows:
            raw = row.get('scnYmd', '')
            try:
                dates.append(datetime.strptime(raw, '%Y%m%d').date())
            except (TypeError, ValueError):
                # hldyYn 등 이 API의 다른 필드가 실제로 null을 내려보내는 것이 HAR로 확인되어
                # (test_crawlers_cgv.py의 hldyYn: None 픽스처 참고), scnYmd도 null일 가능성을
                # 방어한다 — raw가 None이면 strptime이 ValueError가 아닌 TypeError를 낸다.
                logger.warning('CGV scnYmd 형식이 예상과 다릅니다: %r', raw)
        return dates

    def _fetch_schedule(self, movie_no: str, target_date: date) -> list[dict]:
        params = {
            'coCd': _CO_CD,
            'siteNo': _SITE_NO,
            'scnYmd': target_date.strftime('%Y%m%d'),
            'movNo': movie_no,
            'rtctlScopCd': _RTCTL_SCOP_CD,
        }
        return self._get(f'{_BASE_URL}/searchSchByMov', params)

    def _get(self, url: str, params: dict) -> list[dict]:
        try:
            response = requests.get(url, params=params, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            # WAF 차단 시 HTTP 200과 함께 JSON이 아닌 HTML 차단 페이지가 올 수 있다 —
            # response.json()을 try 밖에서 호출하면 이 경우 CinemaCrawlerError로 감싸이지 않고
            # 그대로 전파되어, run_showtime_check의 실패 카운터가 증가하지 않고(실패 알림
            # 안전장치 무력화) check_movie_showtime_openings의 다음 상영관(롯데) 처리까지
            # 중단시킬 수 있다. requests의 JSONDecodeError는 RequestException의 서브클래스라
            # 아래 except가 그대로 잡는다.
            payload = response.json()
            rows = payload.get('data') if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise CinemaCrawlerError(f'CGV 응답 형식이 예상과 다릅니다: {url}')
            return rows
        except requests.RequestException as e:
            logger.error('CGV 요청 실패 (url=%s): %s', url, type(e).__name__)
            raise CinemaCrawlerError(f'CGV 요청 실패: {url}') from e

    def _is_imax_row(self, row: dict) -> bool:
        # scnsNm이 키는 있으되 값이 null로 내려올 수 있어(hldyYn: None과 동일한 패턴) get()의
        # 기본값만으로는 부족하다 — `or ''`로 None도 함께 정규화한다.
        screen_name = row.get('scnsNm') or ''
        return row.get('siteNo') == _SITE_NO and _IMAX_SCREEN_KEYWORD in screen_name.lower()

    def _format_time(self, raw: str | None) -> str:
        """"HHMM" 4자리 문자열을 "HH:MM"으로 변환한다. 자정을 넘긴 심야 회차는 "2430"처럼
        24시 이후 표기로 내려오는데(예: 00:30 상영을 전날 스케줄의 연장으로 표시), 그대로
        "24:30"으로 변환한다 — CGV 사이트 자체의 표기 관행이라 굳이 보정하지 않는다.
        예상과 다른 형식(None 포함)이면 빈 문자열로 정규화해 반환한다."""
        raw = raw or ''
        if len(raw) != 4 or not raw.isdigit():
            return raw
        return f'{raw[:2]}:{raw[2:]}'
