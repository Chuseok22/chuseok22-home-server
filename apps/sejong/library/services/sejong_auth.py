import logging
import re
import threading
from dataclasses import dataclass
from typing import Callable, ClassVar, TypeVar
from urllib.parse import unquote, urlparse

import requests

from apps.sejong.auth.services.portal_sso import SejongPortalSSO

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class AuthSession:
    token: str
    session: requests.Session


_LIBSEAT_HOST = 'libseat.sejong.ac.kr'
_SEAT_MAIN = 'https://libseat.sejong.ac.kr/mobile/MA/seatMain.php'
_REQUEST_TIMEOUT = 15
_TOKEN_PARAM_RE = re.compile(r'(?:^|[?&])token=([^&]*)')


class SejongLibraryAuthService:
    """세종대학교 학술정보원(libseat) 인증 서비스.

    1. SejongPortalSSO.login() → ssotoken 획득
    2. GET seatMain.php?token=<ssotoken> → redirect chain에서 libseat token 추출

    로그인 세션은 프로세스 내(클래스 레벨) 캐시로 재사용된다 — 매 호출마다 재로그인하지 않고,
    fetch_with_retry()를 통해 실제로 만료가 감지됐을 때만 재로그인한다. 이 앱은
    `gunicorn --workers 1 --threads 8`(Dockerfile) 단일 프로세스로 배포되므로 프로세스 내
    싱글턴으로 충분하며, 스레드 동시 접근은 _lock + CAS(compare-and-swap)로 보호한다.
    """

    _cached_session: ClassVar[AuthSession | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def create_session(
        self,
        force_refresh: bool = False,
        stale: AuthSession | None = None,
    ) -> AuthSession | None:
        """캐시된 인증 세션을 반환한다. 없거나 강제 갱신 시 SSO 로그인 후 캐시에 저장한다.

        force_refresh=True일 때는 CAS 방식으로 동작한다: `stale`로 넘겨받은 객체가 여전히
        현재 캐시와 동일할 때만(is 비교) 실제로 재로그인한다. 이미 다른 스레드가 같은 만료를
        먼저 감지해 캐시를 갱신해뒀다면, 재로그인하지 않고 그 최신 캐시를 그대로 반환한다 —
        이게 없으면 동시 만료 감지 시 스레드 수만큼 중복 로그인이 발생한다.
        """
        if not force_refresh:
            cached = SejongLibraryAuthService._cached_session
            if cached is not None:
                return cached

        with SejongLibraryAuthService._lock:
            cached = SejongLibraryAuthService._cached_session
            if not force_refresh and cached is not None:
                return cached
            if force_refresh and cached is not stale:
                return cached

            new_session = self._login()
            SejongLibraryAuthService._cached_session = new_session
            return new_session

    def _login(self) -> AuthSession | None:
        """실제로 SSO에 로그인하고 libseat 토큰을 교환한다 (캐시를 거치지 않는 내부 헬퍼)."""
        sso = SejongPortalSSO()
        portal = sso.login(rt_url='https://libseat.sejong.ac.kr')
        if not portal:
            return None

        try:
            auth_response = portal.session.get(
                _SEAT_MAIN,
                params={'token': portal.ssotoken},
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            auth_response.raise_for_status()
        except requests.RequestException as e:
            logger.error('seatMain 인증 요청 실패: %s', e)
            return None

        token = _extract_token_from_chain(auth_response)
        if token is None:
            safe_url = _mask_token_in_url(auth_response.url)
            logger.error('학술정보원 토큰 추출 실패. 최종 URL: %s', safe_url)
            return None

        # 토큰 원문은 남기지 않되, 이후 mySeat.php 조회 실패와 상관관계를 볼 수 있도록
        # '+' 포함 여부만 기록한다 (#152 재발 시 원인 판별용).
        logger.debug('학술정보원 토큰 추출 성공 (길이=%d, plus 포함=%s)', len(token), '+' in token)

        return AuthSession(token=token, session=portal.session)

    def fetch_token(self) -> str | None:
        """SSO 로그인 후 libseat 토큰을 반환한다. 실패 시 None."""
        result = self.create_session()
        return result.token if result else None

    def fetch_with_retry(self, operation: Callable[[AuthSession], tuple[T, bool]]) -> T | None:
        """캐시/신규 세션으로 operation을 1회 실행하고, 세션 만료 감지 시 강제 재인증 후
        1회만 재시도한다.

        Args:
            operation: (result, session_expired) 튜플을 반환하는 콜러블.
                session_expired=True일 때만 재시도를 트리거한다 — 네트워크 오류 등 다른
                실패는 재시도하지 않는다.

        Returns:
            operation의 result. 로그인 자체가 실패하면(캐시도 재로그인도 실패) None.
            재인증 직후에도 세션이 만료로 감지되면(인증 상태 이상으로 간주) None.
        """
        auth_session = self.create_session()
        if auth_session is None:
            return None

        result, expired = operation(auth_session)
        if expired:
            logger.warning('세션 만료 감지. 재인증 후 재시도합니다.')
            auth_session = self.create_session(force_refresh=True, stale=auth_session)
            if auth_session is None:
                return None
            result, expired = operation(auth_session)
            if expired:
                logger.error('재인증 직후에도 세션 만료가 감지되었습니다. 인증 상태 이상으로 간주합니다.')
                return None

        return result


def _extract_token_from_chain(response: requests.Response) -> str | None:
    """redirect chain(history + 최종 URL)에서 libseat token 파라미터를 추출한다.

    urllib.parse.parse_qs()는 쿼리 값의 '+'를 공백으로 디코딩해(application/x-www-form-urlencoded
    관례) base64 유사 토큰을 오염시키므로 사용하지 않는다. 정규식으로 원문을 추출한 뒤
    '+'를 건드리지 않는 unquote()로만 퍼센트 인코딩을 해제한다.
    """
    # 최신 URL(response.url) 우선 확인 후 역순 history 순회 — 최종 발급된 토큰 우선 확보
    urls = [response.url, *(r.url for r in reversed(response.history))]

    for url in urls:
        parsed = urlparse(url)
        if parsed.hostname != _LIBSEAT_HOST:
            continue
        match = _TOKEN_PARAM_RE.search(parsed.query)
        if match and match.group(1):
            return unquote(match.group(1))

    return None


def _mask_token_in_url(url: str) -> str:
    """URL에서 token 파라미터 값을 마스킹한다 (로그 노출 방지)."""
    return re.sub(r'(token=)[^&]+', r'\1***', url)
