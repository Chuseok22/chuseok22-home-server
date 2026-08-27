import logging
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_EXPIRED_URL_KEYWORDS = ['/login', 'ssoLogin']
_EXPIRED_BODY_KEYWORDS = ['login_action.jsp', 'mainLogin']


@dataclass(frozen=True)
class ParsedSlot:
    """sroomMap.php/loungeMap.php 공통 시간 슬롯 파싱 결과."""

    time_label: str
    is_available: bool
    room_no: str | None = None
    room_name: str | None = None
    start_time: str | None = None


@dataclass(frozen=True)
class ParsedRoom:
    """sroomMap.php/loungeMap.php 공통 룸(좌석) 파싱 결과."""

    room_name: str
    group_title: str
    slots: tuple[ParsedSlot, ...]


def is_session_expired(response: requests.Response) -> bool:
    """URL redirect 또는 body 키워드로 세션 만료를 감지한다 (이중 확인)."""
    if any(kw in response.url for kw in _EXPIRED_URL_KEYWORDS):
        return True
    if any(kw in response.text for kw in _EXPIRED_BODY_KEYWORDS):
        return True
    return False


def extract_url_param(url: str, key: str) -> str | None:
    """URL 쿼리스트링에서 파라미터 값을 추출한다."""
    values = parse_qs(urlparse(url).query).get(key, [])
    return values[0] if values else None


def parse_room_map_html(html: str) -> list[ParsedRoom]:
    """sroomMap.php/loungeMap.php 응답 HTML에서 룸별 가용 현황을 파싱한다."""
    soup = BeautifulSoup(html, 'lxml')

    group_title_el = soup.select_one('.al-title')
    if not group_title_el:
        logger.warning('그룹 제목(.al-title) 요소를 찾을 수 없습니다. HTML 구조가 변경되었을 수 있습니다.')
    group_title = group_title_el.get_text(strip=True) if group_title_el else ''

    slot_header = soup.select_one('.avl-slot')
    if not slot_header:
        return []

    room_names: list[str] = [
        el.get_text(strip=True)
        for el in slot_header.select('.at-title span')
    ]
    if not room_names:
        return []

    room_slots: dict[str, list[ParsedSlot]] = {name: [] for name in room_names}

    for row in soup.select('.avl-data-slot'):
        time_el = row.select_one('.avl-time')
        if not time_el:
            continue
        time_label = time_el.get_text(strip=True)

        for idx, btn_el in enumerate(row.select('.avl-button')):
            if idx >= len(room_names):
                break
            link = btn_el.select_one('a[href]')
            if link:
                href = link.get('href', '')
                room_slots[room_names[idx]].append(ParsedSlot(
                    time_label=time_label,
                    is_available=True,
                    room_no=extract_url_param(href, 'sroomNo'),
                    room_name=extract_url_param(href, 'sroomName'),
                    start_time=extract_url_param(href, 'startTime'),
                ))
            else:
                room_slots[room_names[idx]].append(ParsedSlot(
                    time_label=time_label,
                    is_available=False,
                ))

    return [
        ParsedRoom(room_name=name, group_title=group_title, slots=tuple(slots))
        for name, slots in room_slots.items()
    ]
