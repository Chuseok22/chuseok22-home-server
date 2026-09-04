import logging
from dataclasses import dataclass
from typing import TypedDict

import requests

from apps.sejong.auth.services.ssl_compat import LegacySSLAdapter
from apps.sejong.library.services._room_map_parser import (
    is_session_expired,
    parse_room_map_html,
)
from apps.sejong.library.services.sejong_auth import SejongLibraryAuthService

logger = logging.getLogger(__name__)

_LOUNGE_MAP_URL = 'https://libseat.sejong.ac.kr/mobile/MA/loungeMap.php'
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


class _LoungeGroupParams(TypedDict):
    sroomTitle: str
    seatCnt: int
    roomGB: str
    userId: str
    seq: str


# loungeList.php 링크 전수 분석으로 확정된 6개 S-Lounge 그룹.
# "S-Loung 4인석"은 오타가 아니라 실제 시스템의 sroomTitle 값 그대로다.
# userId는 스터디룸과 동일하게 빈 문자열로 시도한다 — 실패 시 재검증 필요(스펙의 "위험 요소" 참고).
_LOUNGE_GROUPS: list[_LoungeGroupParams] = [
    {'sroomTitle': 'S-Lounge 6인석', 'seatCnt': 6, 'roomGB': 'S3', 'userId': '', 'seq': '0'},
    {'sroomTitle': 'S-Lounge 6인석', 'seatCnt': 6, 'roomGB': 'S3', 'userId': '', 'seq': '1'},
    {'sroomTitle': 'S-Lounge 6인석', 'seatCnt': 6, 'roomGB': 'S3', 'userId': '', 'seq': '2'},
    {'sroomTitle': 'S-Loung 4인석', 'seatCnt': 4, 'roomGB': 'S3', 'userId': '', 'seq': '0'},
    {'sroomTitle': 'S-Loung 4인석', 'seatCnt': 4, 'roomGB': 'S3', 'userId': '', 'seq': '1'},
    {'sroomTitle': 'S-Loung 4인석', 'seatCnt': 4, 'roomGB': 'S3', 'userId': '', 'seq': '2'},
]


@dataclass(frozen=True)
class LoungeSlot:
    time_label: str
    is_available: bool
    room_no: str | None = None
    room_name: str | None = None
    start_time: str | None = None
    room_gb: str | None = None
    sroom_title: str | None = None
    seq: str | None = None


@dataclass(frozen=True)
class Lounge:
    room_name: str    # 예: "SL1"
    group_title: str  # 예: "S-Lounge 6인석"
    seat_cnt: int
    room_gb: str
    sroom_title: str
    seq: str
    slots: tuple[LoungeSlot, ...]


class SloungeService:
    """학술정보원 전체 S-Lounge 가용 현황 조회 서비스"""

    def __init__(self) -> None:
        self._auth = SejongLibraryAuthService()

    def fetch_all_lounges(self, reserve_date: str) -> list[Lounge]:
        """전체 S-Lounge 가용 현황을 반환한다.

        세션은 SejongLibraryAuthService가 캐싱하며, 만료 감지 시에만 재인증 후 1회 재시도한다.
        """
        result = self._auth.fetch_with_retry(
            lambda auth_session: self._fetch_with_token(auth_session.token, reserve_date)
        )
        return result if result is not None else []

    def _fetch_with_token(
        self,
        token: str,
        reserve_date: str,
    ) -> tuple[list[Lounge], bool]:
        session = requests.Session()
        session.headers.update(_HEADERS)
        session.mount('https://', LegacySSLAdapter())

        lounges: list[Lounge] = []
        for group_params in _LOUNGE_GROUPS:
            result = self._fetch_group(session, token, group_params, reserve_date)
            if result is None:
                return [], True
            lounges.extend(result)

        return lounges, False

    def _fetch_group(
        self,
        session: requests.Session,
        token: str,
        group_params: _LoungeGroupParams,
        reserve_date: str,
    ) -> list[Lounge] | None:
        params = {**group_params, 'token': token, 'reserveDate': reserve_date}
        try:
            response = session.get(_LOUNGE_MAP_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
        except requests.RequestException as e:
            logger.error(
                'S-Lounge 그룹 조회 실패 (sroomTitle=%s, seq=%s): %s',
                group_params['sroomTitle'],
                group_params['seq'],
                e,
            )
            return []

        if is_session_expired(response):
            return None

        return [
            Lounge(
                room_name=parsed_room.room_name,
                group_title=parsed_room.group_title,
                seat_cnt=group_params['seatCnt'],
                room_gb=group_params['roomGB'],
                sroom_title=group_params['sroomTitle'],
                seq=group_params['seq'],
                slots=tuple(
                    LoungeSlot(
                        time_label=slot.time_label,
                        is_available=slot.is_available,
                        room_no=slot.room_no,
                        room_name=slot.room_name,
                        start_time=slot.start_time,
                        room_gb=group_params['roomGB'] if slot.is_available else None,
                        sroom_title=group_params['sroomTitle'] if slot.is_available else None,
                        seq=group_params['seq'] if slot.is_available else None,
                    )
                    for slot in parsed_room.slots
                ),
            )
            for parsed_room in parse_room_map_html(response.text)
        ]
