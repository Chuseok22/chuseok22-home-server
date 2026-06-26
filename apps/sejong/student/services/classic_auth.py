import logging

import requests
from django.conf import settings

from apps.sejong.auth.services.portal_sso import SejongPortalSSO

logger = logging.getLogger(__name__)

_CLASSIC_BASE_URL = 'https://classic.sejong.ac.kr'
_REQUEST_TIMEOUT = 15

_SEARCH_HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': f'{_CLASSIC_BASE_URL}/classic/creative/register-write.do',
}


class SejongClassicAuthService:
    """classic.sejong.ac.kr CMS 세션 인증 서비스.

    1. SejongPortalSSO.login() → ssotoken 획득
    2. classic.sejong.ac.kr SSO 콜백 → CMS_JSESSIONID 획득
    """

    def create_session(self) -> requests.Session | None:
        """classic.sejong.ac.kr 인증 세션 반환. 실패 시 None."""
        try:
            sso = SejongPortalSSO()
        except ValueError as e:
            logger.error('포털 SSO 초기화 실패: %s', e)
            return None

        portal = sso.login(rt_url=_CLASSIC_BASE_URL)
        if not portal:
            return None

        sso_callback_path = settings.SEJONG_CLASSIC_SSO_CALLBACK_PATH
        callback_url = f'{_CLASSIC_BASE_URL}{sso_callback_path}'
        try:
            resp = portal.session.get(
                callback_url,
                # ssotoken은 포털 로그인 시 이미 세션 쿠키에 포함됨, returnUrl만 전달
                params={'returnUrl': '/classic/index.do'},
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error('classic.sejong.ac.kr CMS 세션 획득 실패: %s', e)
            return None

        if not portal.session.cookies.get('CMS_JSESSIONID'):
            logger.error(
                'CMS_JSESSIONID 쿠키 없음. SEJONG_CLASSIC_SSO_CALLBACK_PATH(%s) 확인 필요.',
                sso_callback_path,
            )
            return None

        # 이후 요청에서 사용할 헤더 사전 설정
        portal.session.headers.update(_SEARCH_HEADERS)
        return portal.session
