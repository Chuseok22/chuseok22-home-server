import logging
from dataclasses import dataclass
from typing import TypedDict
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from apps.library.services.sejong_auth import SejongLibraryAuthService
from apps.library.services.ssl_compat import LegacySSLAdapter

logger = logging.getLogger(__name__)

_SROOM_MAP_URL = 'https://libseat.sejong.ac.kr/mobile/MA/sroomMap.php'
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


class _RoomGroupParams(TypedDict):
    sroomTitle: str
    seatCnt: int
    roomGB: str
    userId: str
    seq: str


# sroomList.php HTML 분석으로 확정된 5개 룸 그룹
_ROOM_GROUPS: list[_RoomGroupParams] = [
    {'sroomTitle': '그룹스터디룸12인', 'seatCnt': 12, 'roomGB': 'S1', 'userId': '', 'seq': '0'},
    {'sroomTitle': '그룹스터디룸6인실', 'seatCnt': 6, 'roomGB': 'S1', 'userId': '', 'seq': '0'},  # 02~04
    {'sroomTitle': '그룹스터디룸6인실', 'seatCnt': 6, 'roomGB': 'S1', 'userId': '', 'seq': '1'},  # 05~07
    {'sroomTitle': '그룹스터디룸6인실', 'seatCnt': 6, 'roomGB': 'S1', 'userId': '', 'seq': '2'},  # 08~10
    {'sroomTitle': '그룹스터디룸6인실', 'seatCnt': 6, 'roomGB': 'S1', 'userId': '', 'seq': '3'},  # 11~13
]

# 세션 만료 감지: URL에 포함되는 키워드 (HTTP redirect 방식)
_EXPIRED_URL_KEYWORDS = ['/login', 'ssoLogin']
# 세션 만료 감지: body에 포함되는 키워드 (로그인 HTML 반환 방식)
_EXPIRED_BODY_KEYWORDS = ['login_action.jsp', 'mainLogin']


@dataclass(frozen=True)
class RoomSlot:
    time_label: str       # 예: "09:00"
    is_available: bool
    room_no: str | None = None     # 예약가능 시 sroomNo (예: "4")
    room_name: str | None = None   # 예약가능 시 sroomName (예: "04스터디룸")
    start_time: str | None = None  # 예약가능 시 startTime (예: "1000")


@dataclass(frozen=True)
class StudyRoom:
    room_name: str    # 예: "04스터디룸"
    group_title: str  # 예: "스터디룸 6인실 02~04"
    seat_cnt: int
    slots: tuple[RoomSlot, ...]  # frozen=True와 일관성 유지


class StudyRoomService:
    """학술정보원 전체 스터디룸 가용 현황 조회 서비스"""

    def __init__(self) -> None:
        self._auth = SejongLibraryAuthService()

    def fetch_all_rooms(self, reserve_date: str) -> list[StudyRoom]:
        """전체 스터디룸(01~13) 가용 현황을 반환한다.

        세션 만료 감지 시 재인증 후 1회 재시도한다.

        Args:
            reserve_date: 조회 날짜 (YYYYMMDD 형식)

        Returns:
            전체 룸 목록. 인증 실패 또는 조회 오류 시 빈 리스트.
        """
        token = self._auth.fetch_token()
        if token is None:
            return []

        rooms, expired = self._fetch_with_token(token, reserve_date)

        if expired:
            logger.warning('세션 만료 감지. 재인증 후 재시도합니다.')
            token = self._auth.fetch_token()
            if token is None:
                return []
            rooms, _ = self._fetch_with_token(token, reserve_date)

        return rooms

    def _fetch_with_token(
        self,
        token: str,
        reserve_date: str,
    ) -> tuple[list[StudyRoom], bool]:
        """토큰으로 5개 그룹을 순서대로 조회한다.

        Returns:
            (rooms, session_expired) 튜플.
        """
        session = requests.Session()
        session.headers.update(_HEADERS)
        session.mount('https://', LegacySSLAdapter())

        rooms: list[StudyRoom] = []
        for group_params in _ROOM_GROUPS:
            result = self._fetch_group(session, token, group_params, reserve_date)
            if result is None:
                return [], True  # 세션 만료
            rooms.extend(result)

        return rooms, False

    def _fetch_group(
        self,
        session: requests.Session,
        token: str,
        group_params: _RoomGroupParams,
        reserve_date: str,
    ) -> list[StudyRoom] | None:
        """룸 그룹 페이지를 조회해 파싱 결과를 반환한다.

        Returns:
            파싱된 룸 목록. 세션 만료 시 None. 네트워크 오류 시 빈 리스트.
        """
        params = {**group_params, 'token': token, 'reserveDate': reserve_date}
        try:
            response = session.get(_SROOM_MAP_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
        except requests.RequestException as e:
            logger.error(
                '스터디룸 그룹 조회 실패 (sroomTitle=%s, seq=%s): %s',
                group_params['sroomTitle'],
                group_params['seq'],
                e,
            )
            return []

        if _is_session_expired(response):
            return None

        return _parse(response.text, group_params['seatCnt'])


def _is_session_expired(response: requests.Response) -> bool:
    """URL redirect 또는 body 키워드로 세션 만료를 감지한다 (이중 확인)."""
    if any(kw in response.url for kw in _EXPIRED_URL_KEYWORDS):
        return True
    if any(kw in response.text for kw in _EXPIRED_BODY_KEYWORDS):
        return True
    return False


def _parse(html: str, seat_cnt: int) -> list[StudyRoom]:
    """HTML에서 스터디룸 가용 현황을 파싱한다."""
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

    room_slots: dict[str, list[RoomSlot]] = {name: [] for name in room_names}

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
                room_slots[room_names[idx]].append(RoomSlot(
                    time_label=time_label,
                    is_available=True,
                    room_no=_extract_url_param(href, 'sroomNo'),
                    room_name=_extract_url_param(href, 'sroomName'),
                    start_time=_extract_url_param(href, 'startTime'),
                ))
            else:
                room_slots[room_names[idx]].append(RoomSlot(
                    time_label=time_label,
                    is_available=False,
                ))

    return [
        StudyRoom(
            room_name=name,
            group_title=group_title,
            seat_cnt=seat_cnt,
            slots=tuple(slots),
        )
        for name, slots in room_slots.items()
    ]


def _extract_url_param(url: str, key: str) -> str | None:
    """URL 쿼리스트링에서 파라미터 값을 추출한다."""
    values = parse_qs(urlparse(url).query).get(key, [])
    return values[0] if values else None
