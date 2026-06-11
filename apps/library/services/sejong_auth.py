import logging
import re
from urllib.parse import urlparse, parse_qs

import requests
from django.conf import settings

from apps.library.services.ssl_compat import LegacySSLAdapter

logger = logging.getLogger(__name__)

_LOGIN_URL = 'https://portal.sejong.ac.kr/jsp/login/login_action.jsp'
_LOGIN_REFERER = 'https://portal.sejong.ac.kr/jsp/login/loginSSO.jsp'
_LIBSEAT_HOST = 'libseat.sejong.ac.kr'
_SEAT_MAIN = 'https://libseat.sejong.ac.kr/mobile/MA/seatMain.php'
_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}


class SejongLibraryAuthService:
    """세종대학교 포털 SSO 로그인 후 학술정보원 토큰을 추출하는 인증 서비스

    1. POST login_action.jsp → ssotoken 쿠키 획득
    2. GET seatMain.php?token=<ssotoken> → redirect chain
    3. chain 내 URL의 token 파라미터 추출
    """

    def __init__(self) -> None:
        self._student_id: str = settings.SEJONG_STUDENT_ID
        self._password: str = settings.SEJONG_PASSWORD
        if not self._student_id or not self._password:
            raise ValueError('SEJONG_STUDENT_ID 또는 SEJONG_PASSWORD가 설정되지 않았습니다.')

    def fetch_token(self) -> str | None:
        """SSO 로그인 후 libseat 토큰을 반환한다. 실패 시 None."""
        session = requests.Session()
        session.headers.update(_HEADERS)
        session.mount('https://', LegacySSLAdapter())

        # Step 1: POST 로그인 — 200 응답, ssotoken 쿠키 설정됨
        try:
            login_response = session.post(
                _LOGIN_URL,
                data={
                    'mainLogin': 'Y',
                    'rtUrl': 'https://libseat.sejong.ac.kr',
                    'id': self._student_id,
                    'password': self._password,
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': _LOGIN_REFERER,
                },
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=False,
            )
            login_response.raise_for_status()
        except requests.RequestException as e:
            logger.error('학술정보원 로그인 POST 실패: %s', e)
            return None

        # Step 2: ssotoken 쿠키 값 확인
        ssotoken = session.cookies.get('ssotoken')
        if not ssotoken:
            logger.error('ssotoken 쿠키 없음. 로그인 자격증명을 확인하세요.')
            return None

        # Step 3: GET seatMain.php?token=<ssotoken> → redirect chain에서 libseat token 추출
        try:
            auth_response = session.get(
                _SEAT_MAIN,
                params={'token': ssotoken},
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            auth_response.raise_for_status()
        except requests.RequestException as e:
            logger.error('seatMain 인증 요청 실패: %s', e)
            return None

        # Step 4: redirect chain에서 libseat token 추출
        token = _extract_token_from_chain(auth_response)
        if token is None:
            # 주의: auth_response.url에는 token이 포함되므로 직접 로깅 금지.
            # 반드시 _mask_token_in_url()로 마스킹 후 출력.
            safe_url = _mask_token_in_url(auth_response.url)
            logger.error('학술정보원 토큰 추출 실패. 최종 URL: %s', safe_url)
        return token


def _extract_token_from_chain(response: requests.Response) -> str | None:
    """redirect chain(history + 최종 URL)에서 libseat token 파라미터를 추출한다."""
    # r.url: requests가 이미 resolve한 절대 URL (Location 헤더보다 안전)
    urls = [r.url for r in response.history]
    urls.append(response.url)

    for url in urls:
        if not url or _LIBSEAT_HOST not in url:
            continue
        params = parse_qs(urlparse(url).query)
        token_list = params.get('token', [])
        if token_list and token_list[0]:
            return token_list[0]

    return None


def _mask_token_in_url(url: str) -> str:
    """URL에서 token 파라미터 값을 마스킹한다 (로그 노출 방지)."""
    return re.sub(r'(token=)[^&]+', r'\1***', url)
