import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, ClassVar, TypeVar
from urllib.parse import urlparse

import requests
from django.conf import settings

from apps.sejong.auth.services.ssl_compat import LegacySSLAdapter

logger = logging.getLogger(__name__)

T = TypeVar('T')

_LOGIN_PAGE_URL = 'https://ecampus.sejong.ac.kr/login/index.php'
_REQUEST_TIMEOUT = 15
# 로그인 실패 후 재시도까지 최소 대기 시간. Moodle의 lockoutthreshold 정책으로
# 반복 실패 시 실계정이 잠길 위험이 있어 짧은 backoff를 둔다.
_RELOGIN_BACKOFF_SECONDS = 300
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}


class _NetworkLoginError(Exception):
    """로그인 POST 자체가 네트워크 오류(타임아웃, 5xx 등)로 실패했을 때 발생한다.

    자격증명이 실제로 거부된 경우(_login()이 None을 반환)와 구분해야 한다 - 전자는
    계정 잠금과 무관하므로 backoff를 걸면 안 된다.
    """


@dataclass
class EcampusSession:
    session: requests.Session


class EcampusMoodleAuthService:
    """집현캠퍼스(ecampus.sejong.ac.kr, Moodle) 인증 서비스.

    Moodle은 별도 token이 아니라 `MoodleSession` 쿠키로 인증되므로, 세션 캐시 구조는
    apps.sejong.library.services.sejong_auth.SejongLibraryAuthService와 동일한
    ClassVar + Lock + CAS(compare-and-swap) 재인증 패턴을 따르되 `EcampusSession`은
    session 필드만 가진다.
    """

    _cached_session: ClassVar[EcampusSession | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _last_login_failure_at: ClassVar[float | None] = None

    def create_session(
        self,
        force_refresh: bool = False,
        stale: EcampusSession | None = None,
    ) -> EcampusSession | None:
        """캐시된 인증 세션을 반환한다. 없거나 강제 갱신 시 로그인 후 캐시에 저장한다.

        SejongLibraryAuthService.create_session()과 동일한 CAS 방식으로 동작한다.
        """
        if not force_refresh:
            cached = EcampusMoodleAuthService._cached_session
            if cached is not None:
                return cached

        with EcampusMoodleAuthService._lock:
            cached = EcampusMoodleAuthService._cached_session
            if not force_refresh and cached is not None:
                return cached
            if force_refresh and cached is not stale:
                return cached

            if not self._can_attempt_login():
                logger.warning('최근 로그인 실패 이후 backoff 기간 중입니다. 재로그인을 건너뜁니다.')
                return None

            try:
                new_session = self._login()
            except _NetworkLoginError:
                # 네트워크 오류는 자격증명 거부가 아니므로 backoff를 걸지 않는다.
                new_session = None
            else:
                if new_session is None:
                    EcampusMoodleAuthService._last_login_failure_at = time.monotonic()
            EcampusMoodleAuthService._cached_session = new_session
            return new_session

    def fetch_with_retry(self, operation: Callable[[EcampusSession], tuple[T, bool]]) -> T | None:
        """캐시/신규 세션으로 operation을 1회 실행하고, 세션 만료 감지 시 강제 재인증 후
        1회만 재시도한다.

        apps.sejong.library.services.sejong_auth.SejongLibraryAuthService.fetch_with_retry와
        동일한 패턴이다.

        Args:
            operation: (result, session_expired) 튜플을 반환하는 콜러블.
                session_expired=True일 때만 재시도를 트리거한다 — 네트워크 오류 등 다른
                실패는 재시도하지 않는다.

        Returns:
            operation의 result. 로그인 자체가 실패하면(캐시도 재로그인도 실패) None.
            재인증 직후에도 세션이 만료로 감지되면(인증 상태 이상으로 간주) None.
        """
        ecampus_session = self.create_session()
        if ecampus_session is None:
            return None

        result, expired = operation(ecampus_session)
        if expired:
            logger.warning('세션 만료 감지. 재인증 후 재시도합니다.')
            ecampus_session = self.create_session(force_refresh=True, stale=ecampus_session)
            if ecampus_session is None:
                return None
            result, expired = operation(ecampus_session)
            if expired:
                logger.error('재인증 직후에도 세션 만료가 감지되었습니다. 인증 상태 이상으로 간주합니다.')
                return None

        return result

    def _can_attempt_login(self) -> bool:
        last_failure = EcampusMoodleAuthService._last_login_failure_at
        if last_failure is None:
            return True
        return (time.monotonic() - last_failure) >= _RELOGIN_BACKOFF_SECONDS

    def _login(self) -> EcampusSession | None:
        """실제로 Moodle SSO 폼에 로그인한다 (캐시를 거치지 않는 내부 헬퍼).

        네트워크 오류(타임아웃, 5xx 등)는 `_NetworkLoginError`를 일으킨다 - 자격증명
        거부와 구분해서 backoff 대상에서 제외하기 위함(create_session() 참고). 자격증명이
        실제로 거부된 경우에만 None을 반환한다.
        """
        student_id = settings.SEJONG_STUDENT_ID
        password = settings.SEJONG_PASSWORD
        if not student_id or not password:
            logger.error('SEJONG_STUDENT_ID 또는 SEJONG_PASSWORD가 설정되지 않았습니다.')
            return None

        session = requests.Session()
        session.headers.update(_HEADERS)
        session.mount('https://', LegacySSLAdapter())

        try:
            response = session.post(
                _LOGIN_PAGE_URL,
                data={
                    'ssoGubun': 'Login',
                    'type': 'popup_login',
                    'username': student_id,
                    'password': password,
                    'loginbutton': '로그인',
                },
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('집현캠퍼스 로그인 POST 실패: %s', e)
            raise _NetworkLoginError from e

        if not _is_login_successful(response):
            logger.error('집현캠퍼스 로그인 실패. 최종 URL: %s', response.url)
            return None

        return EcampusSession(session=session)


def _is_login_successful(response: requests.Response) -> bool:
    """로그인 성공 여부를 판정한다.

    `MoodleSession` 쿠키 존재만으로는 판정할 수 없다 — `/login/index.php`를 익명 GET만
    해도 이 쿠키가 발급되기 때문이다(실계정 스파이크로 확인됨). 대신 응답이 로그인
    페이지가 아닌 다른 URL로 리다이렉트됐고, 응답 본문에 `logout.php` 링크가 존재하는지로
    판정한다.
    """
    if urlparse(response.url).path == '/login/index.php':
        return False
    return 'logout.php' in response.text
