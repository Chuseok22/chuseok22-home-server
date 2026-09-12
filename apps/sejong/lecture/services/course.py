import functools
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService, EcampusSession

logger = logging.getLogger(__name__)

_COURSE_VIEW_URL = 'https://ecampus.sejong.ac.kr/course/view.php'
_PAST_COURSES_URL = 'https://ecampus.sejong.ac.kr/local/ubion/user/index.php'
_VIEWER_URL = 'https://ecampus.sejong.ac.kr/mod/vod/viewer.php'
_LOGIN_REDIRECT_PATHS = {'/login/index.php', '/login.php'}
_REQUEST_TIMEOUT = 15

_COURSE_ID_RE = re.compile(r'id=(\d+)')
_LECTURE_ID_RE = re.compile(r'module-(\d+)')
# https만 허용 - CDN 인증 토큰이 URL 경로에 포함되므로 http로 노출되면 전송 중 그대로 드러난다.
_M3U8_URL_RE = re.compile(r'https://[^\s"\'<>]+index\.m3u8')


@dataclass(frozen=True)
class Course:
    id: str
    name: str
    year: str
    semester: str  # '10'(1학기)/'11'(여름계절수업)/'20'(2학기)/'21'(겨울계절수업)/'all'(라벨을 알 수 없을 때 폴백) 코드값


_SEMESTER_CODE_BY_LABEL = {
    '1학기': '10',
    '여름계절수업': '11',
    '2학기': '20',
    '겨울계절수업': '21',
}
SEMESTER_LABEL_BY_CODE = {code: label for label, code in _SEMESTER_CODE_BY_LABEL.items()}


@dataclass(frozen=True)
class Lecture:
    id: str
    title: str


class EcampusCourseService:
    """집현캠퍼스 강좌/강의 목록 조회 및 스트림 URL 추출 서비스.

    세션 만료(로그인 페이지로 리다이렉트) 감지 시
    EcampusMoodleAuthService.fetch_with_retry()를 통해 자동으로 1회 강제 재인증 후
    재시도한다 — apps.sejong.library.services.my_reservations.MyReservationsService와
    동일한 패턴(서비스가 내부적으로 인증 서비스를 소유하고, 각 조회 메서드는 세션을
    직접 받지 않는다).
    """

    def __init__(self) -> None:
        self._auth = EcampusMoodleAuthService()

    def search_past_courses(self, year: str, semester: str) -> list[Course]:
        """연도/학기로 과거강좌를 검색한다. year/semester는 세종대 select 옵션값을 그대로 받는다
        (예: '2024', 'all', '10', '20', 'all'). 실패 시 빈 리스트를 반환한다."""
        operation = functools.partial(
            self._fetch_past_courses_with_session, year=year, semester=semester,
        )
        result = self._auth.fetch_with_retry(operation)
        return result if result is not None else []

    def _fetch_past_courses_with_session(
        self, ecampus_session: EcampusSession, year: str, semester: str,
    ) -> tuple[list[Course] | None, bool]:
        try:
            response = ecampus_session.session.get(
                _PAST_COURSES_URL,
                params={'year': year, 'semester': semester},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('과거강좌 조회 실패 (year=%s, semester=%s): %s', year, semester, e)
            return None, False

        if not _is_authenticated_page(response):
            return None, True
        return _parse_past_courses(response.text), False

    def find_course(self, course_id: str, year: str, semester: str) -> Course | None:
        """course_id로 강좌를 찾는다. year/semester로 특정한 학기의 조회 결과에서 매칭되는
        강좌를 찾는다."""
        courses = self.search_past_courses(year=year, semester=semester)
        return next((c for c in courses if c.id == course_id), None)

    def list_lectures(self, course_id: str) -> list[Lecture]:
        """코스 페이지에서 강의(영상) 목록을 조회한다. 실패 시 빈 리스트를 반환한다."""
        operation = functools.partial(self._fetch_lectures_with_session, course_id=course_id)
        result = self._auth.fetch_with_retry(operation)
        return result if result is not None else []

    def _fetch_lectures_with_session(
        self, ecampus_session: EcampusSession, course_id: str,
    ) -> tuple[list[Lecture] | None, bool]:
        try:
            response = ecampus_session.session.get(
                _COURSE_VIEW_URL,
                params={'id': course_id},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('강의 목록 조회 실패 (course_id=%s): %s', course_id, e)
            return None, False

        if _is_moodle_login_redirect(response):
            return None, True
        return _parse_lectures(response.text), False

    def get_stream_url(self, lecture_id: str) -> str | None:
        """강의의 `index.m3u8` 스트림 URL을 추출한다.

        CDN URL에 포함된 인증 토큰의 TTL이 짧을 수 있으므로 이 메서드는 결과를 캐시하지
        않는다 — 다운로드를 시작하기 직전에만 호출할 것(세션 재인증은 하되 URL 자체는
        절대 캐시하지 않는다).
        """
        operation = functools.partial(self._fetch_stream_url_with_session, lecture_id=lecture_id)
        return self._auth.fetch_with_retry(operation)

    def _fetch_stream_url_with_session(
        self, ecampus_session: EcampusSession, lecture_id: str,
    ) -> tuple[str | None, bool]:
        try:
            response = ecampus_session.session.get(
                _VIEWER_URL,
                params={'id': lecture_id},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('스트림 URL 조회 실패 (lecture_id=%s): %s', lecture_id, e)
            return None, False

        if _is_moodle_login_redirect(response):
            return None, True

        match = _M3U8_URL_RE.search(response.text)
        if not match:
            logger.error('응답 본문에서 index.m3u8 URL을 찾을 수 없습니다 (lecture_id=%s).', lecture_id)
            return None, False
        return match.group(0), False


def _is_moodle_login_redirect(response: requests.Response) -> bool:
    """course/view.php, viewer.php 용 - 경로 기반 세션 만료 판정.

    Moodle이 세션 만료 시 리다이렉트하는 로그인 경로가 페이지마다 다름을 실측으로 확인했다
    (/my/ -> /login/index.php, 과거강좌 페이지 -> /login.php). 이 함수는 두 경로를 모두 인식한다.
    """
    return urlparse(response.url).path in _LOGIN_REDIRECT_PATHS


def _is_authenticated_page(response: requests.Response) -> bool:
    """local/ubion/user/index.php 용 - 컨텐츠 기반 판정.

    이 페이지는 세션 만료 시 리다이렉트 없이 빈 위젯을 담은 200 응답을 줄 수 있어(집현캠퍼스
    강좌 목록 조회 실패 버그의 근본 원인이었다), 경로 대신 페이지 본문에 로그아웃 링크(logout.php)
    가 있는지로 인증 여부를 판정한다. course/view.php에는 이 문자열이 없음을 실측으로 확인했으므로
    그 페이지에는 이 함수를 쓰지 않는다.
    """
    return 'logout.php' in response.text


def _parse_past_courses(html: str) -> list[Course]:
    """`local/ubion/user/index.php` 검색 결과 테이블을 파싱한다.

    `a.coursefullname`은 뱃지가 앵커 밖에 있어 텍스트가 이미 깨끗하므로 `get_text(strip=True)`를
    그대로 쓴다. 같은 `<tr>` 안의 앞쪽 두 `<td>`(연도, 학기)를 함께 읽어 `Course.year`/
    `Course.semester`에 담는다 - 학기 필터링/그룹핑에 쓰인다. 학기는 화면에 보이는 한글 라벨이
    아니라 `_SEMESTER_CODE_BY_LABEL`로 변환한 코드값을 저장한다(select 필드·재조회 쿼리
    파라미터와 동일한 값 체계를 유지하기 위함). 알 수 없는 라벨은 `'all'`로 폴백한다 - 원문을
    그대로 두면 그 값이 ChoiceField 검증을 통과하지 못해 이 강좌를 클릭했을 때 조회 자체가
    실패하게 된다. `'all'`로 두면 그룹 헤더 표시만 다소 어색해질 뿐 클릭/다운로드는 계속 동작한다.
    """
    soup = BeautifulSoup(html, 'lxml')
    courses: dict[str, Course] = {}
    for link in soup.select('a.coursefullname[href*="course/view.php?id="]'):
        match = _COURSE_ID_RE.search(link.get('href', ''))
        if not match:
            continue
        name = link.get_text(strip=True)
        if not name:
            continue
        row = link.find_parent('tr')
        cells = row.select('td') if row else []
        if len(cells) < 2:
            logger.warning(
                '과거강좌 조회 결과 행에서 연도/학기 <td>를 찾지 못해 강좌를 건너뜀 '
                '(course_id=%s) - HTML 구조 변경 가능성',
                match.group(1),
            )
            continue
        year = cells[0].get_text(strip=True)
        # 연도 셀이 숫자가 아니면(빈 값, 비정상 텍스트 등) 원문을 그대로 두지 않고 'all'로
        # 폴백한다 - semester와 동일한 이유: 원문이 LECTURE_YEAR_CHOICES의 ChoiceField 검증을
        # 통과하지 못하면 이 강좌를 클릭했을 때 조회 자체가 실패하게 된다.
        year = year if year.isdigit() else 'all'
        semester_label = cells[1].get_text(strip=True)
        semester = _SEMESTER_CODE_BY_LABEL.get(semester_label, 'all')
        course_id = match.group(1)
        courses.setdefault(
            course_id, Course(id=course_id, name=name, year=year, semester=semester),
        )
    return list(courses.values())


def _parse_lectures(html: str) -> list[Lecture]:
    """코스 페이지 HTML에서 강의(영상) 목록을 파싱한다."""
    soup = BeautifulSoup(html, 'lxml')
    lectures: list[Lecture] = []
    for item in soup.select('li.activity.vod'):
        match = _LECTURE_ID_RE.search(item.get('id', ''))
        if not match:
            continue
        name_el = item.select_one('span.instancename')
        if not name_el:
            continue
        title = _extract_instance_name(name_el)
        if not title:
            continue
        lectures.append(Lecture(id=match.group(1), title=title))
    return lectures


def _extract_instance_name(name_el: Tag) -> str:
    """`instancename` span에서 중첩된 `accesshide` 텍스트(예: " 동영상")를 제외한
    순수 제목만 추출한다 — 문서 순서상 가장 먼저 나오는 문자열만 취한다."""
    return next(name_el.stripped_strings, '')
