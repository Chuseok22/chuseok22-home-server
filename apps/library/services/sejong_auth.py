import logging
import re
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)

_LOGIN_URL = 'https://portal.sejong.ac.kr/jsp/login/login_action.jsp'
_LIBSEAT_HOST = 'libseat.sejong.ac.kr'
_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


class SejongLibraryAuthService:
    """세종대학교 포털 SSO 로그인 후 학술정보원 토큰을 추출하는 인증 서비스

    login_action.jsp는 200 + JS redirect 방식이므로:
    1. POST login → 200 + ssotoken 쿠키 + body에 eproxy URL
    2. body에서 eproxy URL 파싱
    3. GET eproxy (쿠키 자동 포함) → libseat redirect chain
    4. chain에서 token 파라미터 추출
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

        # Step 1: POST 로그인 — 200 응답, ssotoken 쿠키 설정됨
        try:
            login_response = session.post(
                _LOGIN_URL,
                data={
                    'mainLogin': 'Y',
                    'rtUrl': 'https://library.sejong.ac.kr',
                    'id': self._student_id,
                    'password': self._password,
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=False,  # JS redirect이므로 자동 추적 비활성화
            )
            login_response.raise_for_status()
        except requests.RequestException as e:
            logger.error('학술정보원 로그인 POST 실패: %s', e)
            return None

        # Step 2: body에서 eproxy URL 추출
        eproxy_url = _extract_redirect_url(login_response.text)
        if not eproxy_url:
            logger.error('eproxy URL 추출 실패. 로그인 자격증명 또는 응답 형식을 확인하세요.')
            return None

        # Step 3: GET eproxy — ssotoken 쿠키가 세션에 포함된 상태로 전송
        try:
            auth_response = session.get(
                eproxy_url,
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,  # eproxy 이후는 HTTP redirect 체인
            )
            auth_response.raise_for_status()
        except requests.RequestException as e:
            logger.error('eproxy 인증 요청 실패: %s', e)
            return None

        # Step 4: redirect chain에서 libseat token 추출
        token = _extract_token_from_chain(auth_response)
        if token is None:
            # 주의: auth_response.url에는 token이 포함되므로 직접 로깅 금지.
            # 반드시 _mask_token_in_url()로 마스킹 후 출력.
            safe_url = _mask_token_in_url(auth_response.url)
            logger.error('학술정보원 토큰 추출 실패. 최종 URL: %s', safe_url)
        return token


def _extract_redirect_url(html: str) -> str | None:
    """200 응답 HTML/JS body에서 리다이렉트 대상 URL을 추출한다.

    다음 패턴을 순서대로 시도한다:
    1. location.href = "URL" (JS 코드)
    2. <meta http-equiv="refresh" content="0; url=URL">
    """
    soup = BeautifulSoup(html, 'lxml')

    # 패턴 1: JS location.href
    script_text = ' '.join(tag.get_text() for tag in soup.select('script'))
    match = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', script_text)
    if match:
        return match.group(1)

    # 패턴 2: meta refresh
    meta = soup.select_one('meta[http-equiv="refresh"]')
    if meta:
        content = meta.get('content', '')
        url_match = re.search(r'url=(.+)', content, re.IGNORECASE)
        if url_match:
            return url_match.group(1).strip().strip("'\"")

    return None


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
