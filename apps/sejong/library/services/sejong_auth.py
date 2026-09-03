import logging
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

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
_TOKEN_PARAM_RE = re.compile(r'(?:^|[?&])token=([^&]*)')


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

        # 토큰 원문은 남기지 않되, 이후 mySeat.php 조회 실패와 상관관계를 볼 수 있도록
        # '+' 포함 여부만 기록한다 (#152 재발 시 원인 판별용).
        logger.debug('학술정보원 토큰 추출 성공 (길이=%d, plus 포함=%s)', len(token), '+' in token)

        return AuthSession(token=token, session=portal.session)

    def fetch_token(self) -> str | None:
        """SSO 로그인 후 libseat 토큰을 반환한다. 실패 시 None."""
        result = self.create_session()
        return result.token if result else None


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
