import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_LOGIN_URL = 'https://www.dreamspon.com/process/checkuser.html'
_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


@dataclass
class DreamsponSession:
    session: requests.Session


class DreamsponAuth:
    """드림스폰(dreamspon.com) 로그인 서비스.

    dreamspon.com에 로그인해 PHPSESSID 세션 쿠키가 포함된 인증 세션을 반환한다.
    일반장학금 상세 페이지의 선발대상·장학종류 등은 로그인 후에만 노출되므로
    DreamsponCrawler.crawl_detail()에서 상세 페이지 요청 시 사용한다.
    """

    def __init__(self) -> None:
        self._user_id: str = settings.DREAMSPON_ID
        self._password: str = settings.DREAMSPON_PASSWORD
        if not self._user_id or not self._password:
            raise ValueError('DREAMSPON_ID 또는 DREAMSPON_PASSWORD가 설정되지 않았습니다.')

    def login(self) -> DreamsponSession | None:
        """드림스폰 로그인. 성공 시 인증된 세션 반환, 실패 시 None."""
        session = requests.Session()
        session.headers.update(_HEADERS)

        try:
            response = session.post(
                _LOGIN_URL,
                data={
                    'mode': 'login',
                    'userid': self._user_id,
                    'userpw': self._password,
                    'idsaveCheck': '',
                    'autoLogin': 'N',
                    'pageReferer': '',
                },
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error('드림스폰 로그인 요청 실패: %s', e)
            return None

        if not data.get('result') or data.get('checkyn') != 'Y':
            logger.error('드림스폰 로그인 실패: 자격증명을 확인하세요.')
            return None

        return DreamsponSession(session=session)
