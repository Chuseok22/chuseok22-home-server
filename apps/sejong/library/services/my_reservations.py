import logging
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from apps.sejong.auth.services.ssl_compat import LegacySSLAdapter
from apps.sejong.library.services.sejong_auth import SejongLibraryAuthService

logger = logging.getLogger(__name__)

_MY_SEAT_URL = 'https://libseat.sejong.ac.kr/mobile/MA/mySeat.php'
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}
# mySeat.php의 .tab-content는 항상 이 순서로 렌더링된다 (실제 캡처 HTML에서 확인).
_CATEGORY_ORDER = ('열람실', '스터디룸', '시네마룸', 'S-Lounge')
_CANCEL_ID_RE = re.compile(r"""cancelSroom\(['"](\d+)['"]\)""")


@dataclass(frozen=True)
class MyReservationItem:
    category: str
    date: str
    time_range: str
    room_name: str
    status_text: str
    is_active: bool
    reservation_no: str | None = None


class MyReservationsService:
    """mySeat.php 기반 실시간 예약 현황(열람실·스터디룸·시네마룸·S-Lounge) 조회 서비스"""

    def __init__(self) -> None:
        self._auth = SejongLibraryAuthService()

    def fetch_all(self) -> list[MyReservationItem] | None:
        """전체 예약 현황을 반환한다.

        인증 실패/네트워크 오류 시 빈 리스트, 응답 HTML 구조가 예상과 다르면(마크업 개편 등)
        `None`을 반환해 "예약 없음"과 "파싱 실패"를 구분한다.
        """
        auth_session = self._auth.create_session()
        if auth_session is None:
            return []

        session = auth_session.session
        session.headers.update(_HEADERS)
        session.mount('https://', LegacySSLAdapter())

        try:
            response = session.get(
                _MY_SEAT_URL,
                params={'token': auth_session.token},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
        except requests.RequestException as e:
            logger.error('내 예약 현황 조회 실패: %s', e)
            return []

        return _parse_my_seat_html(response.text)


def _parse_my_seat_html(html: str) -> list[MyReservationItem] | None:
    """mySeat.php 응답 HTML의 4개 탭(.tab-content)을 고정 순서로 파싱한다.

    tab-content 개수가 4개(_CATEGORY_ORDER)와 다르면 마크업이 변경된 것으로 보고 None을 반환한다.
    """
    soup = BeautifulSoup(html, 'lxml')
    tab_contents = soup.select('.tab-content')

    if len(tab_contents) != len(_CATEGORY_ORDER):
        logger.error(
            '내 예약 현황 HTML 구조가 예상과 다릅니다 (tab-content 개수=%d, 예상=%d). '
            '마크업이 변경되었을 수 있습니다.',
            len(tab_contents), len(_CATEGORY_ORDER),
        )
        return None

    items: list[MyReservationItem] = []
    for category, tab in zip(_CATEGORY_ORDER, tab_contents):
        for item_el in tab.select('.item'):
            items.append(_parse_item(category, item_el))
    return items


def _parse_item(category: str, item_el: Tag) -> MyReservationItem:
    date_el = item_el.select_one('.date')
    time_el = item_el.select_one('.info .time')
    room_el = item_el.select_one('.info .room')
    status_el = item_el.select_one('.status')

    status_text = status_el.get_text(strip=True) if status_el else ''
    is_confirm = bool(status_el and 'confirm' in status_el.get('class', []))

    reservation_no = None
    if not is_confirm and status_el:
        onclick = status_el.get('onclick', '')
        match = _CANCEL_ID_RE.search(onclick)
        if match:
            reservation_no = match.group(1)

    return MyReservationItem(
        category=category,
        date=date_el.get_text(strip=True) if date_el else '',
        time_range=time_el.get_text(strip=True) if time_el else '',
        room_name=room_el.get_text(strip=True) if room_el else '',
        status_text=status_text,
        is_active=not is_confirm,
        reservation_no=reservation_no,
    )
