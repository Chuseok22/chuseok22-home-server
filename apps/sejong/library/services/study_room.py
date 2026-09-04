import logging
from dataclasses import dataclass
from typing import TypedDict

import requests

from apps.sejong.auth.services.ssl_compat import LegacySSLAdapter
from apps.sejong.library.services._room_map_parser import (
    is_session_expired as _is_session_expired,
    parse_room_map_html,
)
from apps.sejong.library.services.sejong_auth import SejongLibraryAuthService

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


@dataclass(frozen=True)
class RoomSlot:
    time_label: str       # 예: "09:00"
    is_available: bool
    room_no: str | None = None      # 예약가능 시 sroomNo (예: "4")
    room_name: str | None = None    # 예약가능 시 sroomName (예: "04스터디룸")
    start_time: str | None = None   # 예약가능 시 startTime (예: "1000")
    room_gb: str | None = None      # 예약 API 파라미터 (예약가능 시 non-null)
    sroom_title: str | None = None  # 예약 API 파라미터 (예약가능 시 non-null)
    seq: str | None = None          # 예약 API 파라미터 (예약가능 시 non-null)


@dataclass(frozen=True)
class StudyRoom:
    room_name: str    # 예: "04스터디룸"
    group_title: str  # 예: "스터디룸 6인실 02~04"
    seat_cnt: int
    room_gb: str      # 예약 API 파라미터: 예) "S1"
    sroom_title: str  # 예약 API 파라미터: 예) "그룹스터디룸6인실"
    seq: str          # 예약 API 파라미터: 예) "0"
    slots: tuple[RoomSlot, ...]  # frozen=True와 일관성 유지


class StudyRoomService:
    """학술정보원 전체 스터디룸 가용 현황 조회 서비스"""

    def __init__(self) -> None:
        self._auth = SejongLibraryAuthService()

    def fetch_all_rooms(self, reserve_date: str) -> list[StudyRoom]:
        """전체 스터디룸(01~13) 가용 현황을 반환한다.

        세션은 SejongLibraryAuthService가 캐싱하며, 만료 감지 시에만 재인증 후 1회 재시도한다.

        Args:
            reserve_date: 조회 날짜 (YYYYMMDD 형식)

        Returns:
            전체 룸 목록. 인증 실패 또는 조회 오류 시 빈 리스트.
        """
        result = self._auth.fetch_with_retry(
            lambda auth_session: self._fetch_with_token(auth_session.token, reserve_date)
        )
        return result if result is not None else []

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

        return _parse(
            response.text,
            group_params['seatCnt'],
            group_params['roomGB'],
            group_params['sroomTitle'],
            group_params['seq'],
        )


def _parse(html: str, seat_cnt: int, room_gb: str, sroom_title: str, seq: str) -> list[StudyRoom]:
    """공통 파서(_room_map_parser)의 결과를 StudyRoom/RoomSlot으로 감싼다."""
    return [
        StudyRoom(
            room_name=parsed_room.room_name,
            group_title=parsed_room.group_title,
            seat_cnt=seat_cnt,
            room_gb=room_gb,
            sroom_title=sroom_title,
            seq=seq,
            slots=tuple(
                RoomSlot(
                    time_label=slot.time_label,
                    is_available=slot.is_available,
                    room_no=slot.room_no,
                    room_name=slot.room_name,
                    start_time=slot.start_time,
                    room_gb=room_gb if slot.is_available else None,
                    sroom_title=sroom_title if slot.is_available else None,
                    seq=seq if slot.is_available else None,
                )
                for slot in parsed_room.slots
            ),
        )
        for parsed_room in parse_room_map_html(html)
    ]
