import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

import requests

from apps.sejong.auth.services.portal_sso import SejongPortalSSO

logger = logging.getLogger(__name__)


@dataclass
class AuthSession:
    token: str
    session: requests.Session


_LIBSEAT_HOST = 'libseat.sejong.ac.kr'
_SEAT_MAIN = 'https://libseat.sejong.ac.kr/mobile/MA/seatMain.php'
_REQUEST_TIMEOUT = 15


class SejongLibraryAuthService:
    """세종대학교 학술정보원(libseat) 인증 서비스.

    1. SejongPortalSSO.login() → ssotoken 획득
    2. GET seatMain.php?token=<ssotoken> → redirect chain에서 libseat token 추출
    """

    def create_session(self) -> AuthSession | None:
        """SSO 로그인 후 인증된 세션과 libseat 토큰을 반환한다. 실패 시 None."""
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

        return AuthSession(token=token, session=portal.session)

    def fetch_token(self) -> str | None:
        """SSO 로그인 후 libseat 토큰을 반환한다. 실패 시 None."""
        result = self.create_session()
        return result.token if result else None


def _extract_token_from_chain(response: requests.Response) -> str | None:
    """redirect chain(history + 최종 URL)에서 libseat token 파라미터를 추출한다."""
    # 최신 URL(response.url) 우선 확인 후 역순 history 순회 — 최종 발급된 토큰 우선 확보
    urls = [response.url, *(r.url for r in reversed(response.history))]

    for url in urls:
        parsed = urlparse(url)
        if parsed.hostname != _LIBSEAT_HOST:
            continue
        params = parse_qs(parsed.query)
        token_list = params.get('token', [])
        if token_list and token_list[0]:
            return token_list[0]

    return None


def _mask_token_in_url(url: str) -> str:
    """URL에서 token 파라미터 값을 마스킹한다 (로그 노출 방지)."""
    return re.sub(r'(token=)[^&]+', r'\1***', url)
