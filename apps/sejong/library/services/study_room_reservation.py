import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

from apps.sejong.library.services._room_map_parser import is_session_expired
from apps.sejong.library.services.sejong_auth import AuthSession, SejongLibraryAuthService
from apps.sejong.library.services.study_room import StudyRoomService
from apps.sejong.library.services.validation import validate_attendee_count

logger = logging.getLogger(__name__)

_SROOM_RESERVE_MAIN_URL = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserveMain.php'
_SROOM_RESERVE_URL = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserve.php'
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
_AUTH_FAILURE_CODE = 'AUTH_FAIL'  # 9자 — ReservationHistory.result_code(CharField(max_length=10))에
                                   # 저장 가능해야 하므로 반드시 10자 이하로 유지할 것


@dataclass(frozen=True)
class AttendeeParams:
    student_id: str
    name: str


@dataclass(frozen=True)
class ReservationParams:
    room_no: str
    room_gb: str
    seat_cnt: int
    sroom_title: str
    room_name: str
    seq: str
    reserve_date: str   # YYYYMMDD
    start_time: str     # HHMM
    use_time: int       # 60 or 120
    attendees: tuple[AttendeeParams, ...]


@dataclass(frozen=True)
class ReservationResult:
    success: bool
    result_code: str
    result_message: str
    room_no: str = ''
    room_name: str = ''


class StudyRoomReservationService:
    """학술정보원 스터디룸 예약 서비스"""

    def __init__(self) -> None:
        self._auth = SejongLibraryAuthService()

    def reserve(self, params: ReservationParams) -> ReservationResult:
        """스터디룸을 직접 지정해 예약한다."""
        result = self._auth.fetch_with_retry(
            lambda auth_session: self._reserve_with_session(auth_session, params)
        )
        if result is None:
            return ReservationResult(
                success=False,
                result_code=_AUTH_FAILURE_CODE,
                result_message='인증 실패. SEJONG_STUDENT_ID/SEJONG_PASSWORD 설정을 확인하세요.',
            )
        return result

    def _reserve_with_session(
        self,
        auth_session: AuthSession,
        params: ReservationParams,
    ) -> tuple[ReservationResult, bool]:
        """세션으로 예약 페이지 초기화(GET) + 예약 요청(POST)을 순서대로 수행한다.

        두 단계를 하나의 operation으로 묶는 이유: 만료가 두 호출 사이에서 일어날 수 있고,
        재시도 시 두 단계를 처음부터 다시 실행해야 서버측 PHP 세션 상태가 정합하게 다시 서기
        때문이다(초기화만 다시 하고 POST를 건너뛰거나, 그 반대는 의미가 없다).

        Returns:
            (result, session_expired) 튜플. session_expired=True면 fetch_with_retry가 재인증
            후 이 메서드를 처음부터 다시 호출한다 — 이때 함께 반환하는 result는 재시도 자체가
            실패했을 때만(재인증 실패) 그대로 노출되는 placeholder다.
        """
        session = auth_session.session
        token = auth_session.token

        init_response = self._init_reservation_session(session, token, params)
        if init_response is None:
            return (
                ReservationResult(
                    success=False, result_code='-1', result_message='예약 페이지 접근 실패.',
                ),
                False,
            )
        if is_session_expired(init_response):
            return (
                ReservationResult(
                    success=False, result_code='-1', result_message='예약 페이지 접근 실패.',
                ),
                True,
            )

        post_response = self._post_reservation(session, params)
        if post_response is None:
            return (
                ReservationResult(
                    success=False, result_code='-1',
                    result_message='예약 요청 중 네트워크 오류가 발생했습니다.',
                    room_no=params.room_no, room_name=params.room_name,
                ),
                False,
            )
        if is_session_expired(post_response):
            return (
                ReservationResult(
                    success=False, result_code='-1',
                    result_message='예약 요청 중 네트워크 오류가 발생했습니다.',
                    room_no=params.room_no, room_name=params.room_name,
                ),
                True,
            )

        parsed = _parse_reservation_response(post_response.text)
        return (
            ReservationResult(
                success=parsed.success, result_code=parsed.result_code,
                result_message=parsed.result_message,
                room_no=params.room_no, room_name=params.room_name,
            ),
            False,
        )

    def auto_reserve(
        self,
        reserve_date: str,
        start_time: str,
        use_time: int,
        attendees: tuple[AttendeeParams, ...],
    ) -> ReservationResult:
        """가용 룸을 자동으로 찾아 예약한다.

        조건:
          - start_time 슬롯이 예약 가능
          - ceil(seat_cnt / 2) <= len(attendees) <= seat_cnt
        """
        service = StudyRoomService()
        rooms = service.fetch_all_rooms(reserve_date)

        if not rooms:
            return ReservationResult(
                success=False,
                result_code='-1',
                result_message='스터디룸 조회 실패. 잠시 후 다시 시도하세요.',
            )

        attendee_count = len(attendees)
        for room in rooms:
            if validate_attendee_count(room.seat_cnt, attendee_count) is not None:
                continue

            for slot in room.slots:
                if not slot.is_available:
                    continue
                if slot.start_time != start_time:
                    continue
                if slot.room_no is None or slot.room_name is None:
                    continue

                params = ReservationParams(
                    room_no=slot.room_no,
                    room_gb=room.room_gb,
                    seat_cnt=room.seat_cnt,
                    sroom_title=room.sroom_title,
                    room_name=slot.room_name,
                    seq=room.seq,
                    reserve_date=reserve_date,
                    start_time=start_time,
                    use_time=use_time,
                    attendees=attendees,
                )
                result = self.reserve(params)
                if result.success:
                    return result
                if result.result_code == _AUTH_FAILURE_CODE:
                    logger.error(
                        '인증 실패로 후보 룸 탐색을 중단합니다 (roomNo=%s).', slot.room_no,
                    )
                    return result
                # 예약 실패(경쟁 등) 시 다음 후보 룸 탐색 계속
                logger.warning(
                    '후보 룸 예약 실패 (roomNo=%s, code=%s). 다음 후보 탐색.',
                    slot.room_no,
                    result.result_code,
                )

        return ReservationResult(
            success=False,
            result_code='-1',
            result_message=(
                f'{start_time[:2]}:{start_time[2:]} 시작 가능하고 '
                f'{attendee_count}명 수용 가능한 스터디룸이 없습니다.'
            ),
        )

    def _init_reservation_session(
        self,
        session: requests.Session,
        token: str,
        params: ReservationParams,
    ) -> requests.Response | None:
        """sroomReserveMain.php GET으로 PHP 세션을 수립한다.

        응답을 그대로 반환한다(만료 판정은 호출자인 _reserve_with_session이 한다).
        네트워크 오류 시 None.
        """
        try:
            response = session.get(
                _SROOM_RESERVE_MAIN_URL,
                params={
                    'token': token,
                    'roomGB': params.room_gb,
                    'seatCnt': params.seat_cnt,
                    'sroomTitle': params.sroom_title,
                    'reserveDate': params.reserve_date,
                    'sroomNo': params.room_no,
                    'sroomName': params.room_name,
                    'startTime': params.start_time,
                    'seq': params.seq,
                },
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error('예약 페이지 초기화 실패 (roomNo=%s): %s', params.room_no, e)
            return None

    def _post_reservation(
        self,
        session: requests.Session,
        params: ReservationParams,
    ) -> requests.Response | None:
        """sroomReserve.php POST로 예약을 요청한다.

        응답을 그대로 반환한다(만료 판정·XML 파싱은 호출자인 _reserve_with_session이 한다).
        네트워크 오류 시 None.
        """
        user_ids = '|'.join(a.student_id for a in params.attendees)
        user_names = '|'.join(a.name for a in params.attendees)

        try:
            response = session.post(
                _SROOM_RESERVE_URL,
                data={
                    'userID': user_ids,
                    'userName': user_names,
                    'roomNo': params.room_no,
                    'reserveDate': params.reserve_date,
                    'startTime': params.start_time,
                    'useTime': params.use_time,
                },
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error('예약 요청 실패 (roomNo=%s): %s', params.room_no, e)
            return None


def _parse_reservation_response(xml_text: str) -> ReservationResult:
    """sroomReserve.php XML 응답을 파싱한다.

    응답 형식:
    <?xml version='1.0' encoding='utf-8'?>
    <root><item>
      <resultCode><![CDATA[0]]></resultCode>
      <resultMsg><![CDATA[예약이 완료되었습니다.]]></resultMsg>
    </item></root>
    """
    try:
        root = ET.fromstring(xml_text)
        result_code = root.findtext('item/resultCode') or ''
        result_message = root.findtext('item/resultMsg') or ''
        return ReservationResult(
            success=(result_code == '0'),
            result_code=result_code,
            result_message=result_message,
        )
    except ET.ParseError as e:
        logger.error('예약 응답 XML 파싱 실패: %s\n응답 내용: %.200s', e, xml_text)
        return ReservationResult(
            success=False,
            result_code='-1',
            result_message='서버 응답을 파싱할 수 없습니다.',
        )
