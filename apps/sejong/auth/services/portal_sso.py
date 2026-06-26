import logging
from dataclasses import dataclass

import requests
from django.conf import settings

from apps.sejong.auth.services.ssl_compat import LegacySSLAdapter

logger = logging.getLogger(__name__)

_LOGIN_URL = 'https://portal.sejong.ac.kr/jsp/login/login_action.jsp'
_LOGIN_REFERER = 'https://portal.sejong.ac.kr/jsp/login/loginSSO.jsp'
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


@dataclass
class PortalSession:
    ssotoken: str
    session: requests.Session


class SejongPortalSSO:
    """세종대학교 포털 SSO 로그인 서비스.

    portal.sejong.ac.kr에 로그인하여 ssotoken 쿠키가 포함된 세션을 반환한다.
    하위 시스템(library, student)에서 공유하는 공통 인증 진입점.
    """

    def __init__(self) -> None:
        self._student_id: str = settings.SEJONG_STUDENT_ID
        self._password: str = settings.SEJONG_PASSWORD
        if not self._student_id or not self._password:
            raise ValueError('SEJONG_STUDENT_ID 또는 SEJONG_PASSWORD가 설정되지 않았습니다.')

    def login(self, rt_url: str = '') -> PortalSession | None:
        """포털 SSO 로그인. 성공 시 ssotoken 포함된 PortalSession 반환, 실패 시 None."""
        session = requests.Session()
        session.headers.update(_HEADERS)
        session.mount('https://', LegacySSLAdapter())

        try:
            response = session.post(
                _LOGIN_URL,
                data={
                    'mainLogin': 'Y',
                    'rtUrl': rt_url,
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
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('포털 SSO 로그인 POST 실패: %s', e)
            return None

        ssotoken = session.cookies.get('ssotoken')
        if not ssotoken:
            logger.error('ssotoken 쿠키 없음. 로그인 자격증명을 확인하세요.')
            return None

        return PortalSession(ssotoken=ssotoken, session=session)
