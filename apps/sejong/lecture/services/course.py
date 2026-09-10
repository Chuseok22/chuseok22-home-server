import functools
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService, EcampusSession

logger = logging.getLogger(__name__)

_MY_COURSES_URL = 'https://ecampus.sejong.ac.kr/my/'
_COURSE_VIEW_URL = 'https://ecampus.sejong.ac.kr/course/view.php'
_VIEWER_URL = 'https://ecampus.sejong.ac.kr/mod/vod/viewer.php'
_LOGIN_PAGE_PATH = '/login/index.php'
_REQUEST_TIMEOUT = 15

_COURSE_ID_RE = re.compile(r'id=(\d+)')
_LECTURE_ID_RE = re.compile(r'module-(\d+)')
# https만 허용 - CDN 인증 토큰이 URL 경로에 포함되므로 http로 노출되면 전송 중 그대로 드러난다.
_M3U8_URL_RE = re.compile(r'https://[^\s"\'<>]+index\.m3u8')


@dataclass(frozen=True)
class Course:
    id: str
    name: str


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

    def list_courses(self) -> list[Course]:
        """`/my/` 대시보드에서 강좌 목록을 조회한다. 실패 시 빈 리스트를 반환한다."""
        result = self._auth.fetch_with_retry(self._fetch_courses_with_session)
        return result if result is not None else []

    def _fetch_courses_with_session(
        self, ecampus_session: EcampusSession,
    ) -> tuple[list[Course] | None, bool]:
        try:
            response = ecampus_session.session.get(_MY_COURSES_URL, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('강좌 목록 조회 실패: %s', e)
            return None, False

        if _is_session_expired(response):
            return None, True
        return _parse_courses(response.text), False

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

        if _is_session_expired(response):
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

        if _is_session_expired(response):
            return None, True

        match = _M3U8_URL_RE.search(response.text)
        if not match:
            logger.error('응답 본문에서 index.m3u8 URL을 찾을 수 없습니다 (lecture_id=%s).', lecture_id)
            return None, False
        return match.group(0), False


def _is_session_expired(response: requests.Response) -> bool:
    """응답이 로그인 페이지로 리다이렉트됐으면 Moodle 세션이 만료된 것으로 판정한다."""
    return urlparse(response.url).path == _LOGIN_PAGE_PATH


def _parse_courses(html: str) -> list[Course]:
    """`/my/` 대시보드 HTML에서 강좌 목록을 파싱한다.

    강좌 카드 하나가 썸네일 링크와 제목 링크 등 여러 `<a>`를 가질 수 있어 id 기준으로
    중복을 제거한다(제목 텍스트가 있는 첫 번째 링크만 채택).
    """
    soup = BeautifulSoup(html, 'lxml')
    courses: dict[str, str] = {}
    for link in soup.select('a[href*="course/view.php?id="]'):
        href = link.get('href', '')
        match = _COURSE_ID_RE.search(href)
        if not match:
            continue
        name = link.get_text(strip=True)
        if not name:
            continue
        courses.setdefault(match.group(1), name)
    return [Course(id=course_id, name=name) for course_id, name in courses.items()]


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
