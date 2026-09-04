from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.sejong.library.services.sejong_auth import AuthSession, SejongLibraryAuthService
from apps.sejong.library.services.study_room import RoomSlot, StudyRoom
from apps.sejong.library.services.study_room_reservation import (
    AttendeeParams,
    ReservationParams,
    ReservationResult,
    StudyRoomReservationService,
    _AUTH_FAILURE_CODE,
)


def _make_params(room_no: str = '4', room_name: str = '04스터디룸') -> ReservationParams:
    return ReservationParams(
        room_no=room_no, room_gb='S1', seat_cnt=6, sroom_title='그룹스터디룸6인실',
        room_name=room_name, seq='0', reserve_date='20260901', start_time='1400', use_time=60,
        attendees=(
            AttendeeParams(student_id='22011315', name='백지훈'),
            AttendeeParams(student_id='22011316', name='김철수'),
            AttendeeParams(student_id='22011317', name='이영희'),
        ),
    )


@pytest.fixture(autouse=True)
def _reset_session_cache():
    """test_sejong_auth.py의 autouse fixture는 그 파일에만 적용되므로, 여기서도 별도로
    클래스 레벨 캐시를 리셋한다(이 파일의 일부 테스트가 실제 SejongLibraryAuthService를 사용)."""
    SejongLibraryAuthService._cached_session = None
    yield
    SejongLibraryAuthService._cached_session = None


def test_reserve_returns_auth_failure_result_when_fetch_with_retry_returns_none() -> None:
    service = StudyRoomReservationService()
    service._auth = MagicMock()
    service._auth.fetch_with_retry.return_value = None

    result = service.reserve(_make_params())

    assert result.success is False
    assert result.result_code == _AUTH_FAILURE_CODE
    # reserve()가 create_session()을 직접 호출하는 옛 구현으로 회귀하면 실패해야 한다
    service._auth.fetch_with_retry.assert_called_once()
    service._auth.create_session.assert_not_called()


def test_reserve_with_session_signals_expired_when_init_response_is_login_redirect() -> None:
    service = StudyRoomReservationService()
    session = MagicMock()
    init_response = MagicMock()
    init_response.url = 'https://libseat.sejong.ac.kr/login'
    init_response.text = ''
    init_response.raise_for_status.return_value = None
    session.get.return_value = init_response

    auth_session = AuthSession(token='t', session=session)
    result, expired = service._reserve_with_session(auth_session, _make_params())

    assert expired is True
    session.post.assert_not_called()


def test_reserve_with_session_returns_failure_without_expired_when_init_network_error() -> None:
    service = StudyRoomReservationService()
    session = MagicMock()
    session.get.side_effect = requests.RequestException('boom')

    auth_session = AuthSession(token='t', session=session)
    result, expired = service._reserve_with_session(auth_session, _make_params())

    assert expired is False
    assert result.success is False
    assert result.room_no == ''  # 초기화 단계 실패는 room_no를 채우지 않는다(기존 동작 유지)


def test_reserve_with_session_signals_expired_when_post_response_is_login_redirect() -> None:
    service = StudyRoomReservationService()
    session = MagicMock()

    init_response = MagicMock()
    init_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserveMain.php'
    init_response.text = '<html>ok</html>'
    init_response.raise_for_status.return_value = None

    post_response = MagicMock()
    post_response.url = 'https://libseat.sejong.ac.kr/login'
    post_response.text = ''
    post_response.raise_for_status.return_value = None

    session.get.return_value = init_response
    session.post.return_value = post_response

    auth_session = AuthSession(token='t', session=session)
    result, expired = service._reserve_with_session(auth_session, _make_params())

    assert expired is True


def test_reserve_with_session_returns_success_result() -> None:
    service = StudyRoomReservationService()
    session = MagicMock()

    init_response = MagicMock()
    init_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserveMain.php'
    init_response.text = '<html>ok</html>'
    init_response.raise_for_status.return_value = None

    post_response = MagicMock()
    post_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserve.php'
    post_response.text = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<root><item><resultCode><![CDATA[0]]></resultCode>"
        "<resultMsg><![CDATA[예약이 완료되었습니다.]]></resultMsg></item></root>"
    )
    post_response.raise_for_status.return_value = None

    session.get.return_value = init_response
    session.post.return_value = post_response

    params = _make_params()
    auth_session = AuthSession(token='t', session=session)
    result, expired = service._reserve_with_session(auth_session, params)

    assert expired is False
    assert result.success is True
    assert result.room_no == params.room_no
    assert result.room_name == params.room_name


def test_auto_reserve_aborts_candidate_loop_on_auth_failure() -> None:
    room1 = StudyRoom(
        room_name='01스터디룸', group_title='그룹스터디룸6인실 01~03', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(
            RoomSlot(
                time_label='14:00', is_available=True,
                room_no='1', room_name='01스터디룸', start_time='1400',
                room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
            ),
        ),
    )
    room2 = StudyRoom(
        room_name='02스터디룸', group_title='그룹스터디룸6인실 01~03', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(
            RoomSlot(
                time_label='14:00', is_available=True,
                room_no='2', room_name='02스터디룸', start_time='1400',
                room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
            ),
        ),
    )
    auth_failure_result = ReservationResult(
        success=False, result_code=_AUTH_FAILURE_CODE,
        result_message='인증 실패. SEJONG_STUDENT_ID/SEJONG_PASSWORD 설정을 확인하세요.',
    )
    attendees = (
        AttendeeParams(student_id='22011315', name='백지훈'),
        AttendeeParams(student_id='22011316', name='김철수'),
        AttendeeParams(student_id='22011317', name='이영희'),
    )

    with patch(
        'apps.sejong.library.services.study_room_reservation.StudyRoomService',
    ) as mock_service_cls:
        mock_service_cls.return_value.fetch_all_rooms.return_value = [room1, room2]

        service = StudyRoomReservationService()
        with patch.object(
            StudyRoomReservationService, 'reserve', return_value=auth_failure_result,
        ) as mock_reserve:
            result = service.auto_reserve('20260901', '1400', 60, attendees)

    assert result is auth_failure_result
    mock_reserve.assert_called_once()


def test_auto_reserve_tries_next_candidate_on_non_auth_failure() -> None:
    """인증 실패가 아닌 일반 실패(경쟁 등)는 기존처럼 다음 후보로 계속 넘어가야 한다 —
    "모든 실패에 무조건 중단"으로 잘못 구현해도 앞의 abort 테스트만으로는 못 잡는 케이스."""
    room1 = StudyRoom(
        room_name='01스터디룸', group_title='그룹스터디룸6인실 01~03', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(
            RoomSlot(
                time_label='14:00', is_available=True,
                room_no='1', room_name='01스터디룸', start_time='1400',
                room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
            ),
        ),
    )
    room2 = StudyRoom(
        room_name='02스터디룸', group_title='그룹스터디룸6인실 01~03', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(
            RoomSlot(
                time_label='14:00', is_available=True,
                room_no='2', room_name='02스터디룸', start_time='1400',
                room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
            ),
        ),
    )
    fail_result = ReservationResult(
        success=False, result_code='-1', result_message='경쟁 실패',
        room_no='1', room_name='01스터디룸',
    )
    success_result = ReservationResult(
        success=True, result_code='0', result_message='예약이 완료되었습니다.',
        room_no='2', room_name='02스터디룸',
    )
    attendees = (
        AttendeeParams(student_id='22011315', name='백지훈'),
        AttendeeParams(student_id='22011316', name='김철수'),
        AttendeeParams(student_id='22011317', name='이영희'),
    )

    with patch(
        'apps.sejong.library.services.study_room_reservation.StudyRoomService',
    ) as mock_service_cls:
        mock_service_cls.return_value.fetch_all_rooms.return_value = [room1, room2]

        service = StudyRoomReservationService()
        with patch.object(
            StudyRoomReservationService, 'reserve', side_effect=[fail_result, success_result],
        ) as mock_reserve:
            result = service.auto_reserve('20260901', '1400', 60, attendees)

    assert result is success_result
    assert mock_reserve.call_count == 2


def test_reserve_retries_both_stages_with_fresh_session_after_expiry() -> None:
    """fetch_with_retry를 실제로(mock하지 않고) 통과시켜, 만료 감지 시 _init_reservation_session과
    _post_reservation 두 단계가 새 세션으로 처음부터 다시 실행되는지 검증한다."""
    stale_session = MagicMock()
    stale_expired_response = MagicMock()
    stale_expired_response.url = 'https://libseat.sejong.ac.kr/login'
    stale_expired_response.text = ''
    stale_expired_response.raise_for_status.return_value = None
    stale_session.get.return_value = stale_expired_response

    fresh_session = MagicMock()
    fresh_init_response = MagicMock()
    fresh_init_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserveMain.php'
    fresh_init_response.text = '<html>ok</html>'
    fresh_init_response.raise_for_status.return_value = None
    fresh_post_response = MagicMock()
    fresh_post_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/sroomReserve.php'
    fresh_post_response.text = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<root><item><resultCode><![CDATA[0]]></resultCode>"
        "<resultMsg><![CDATA[예약이 완료되었습니다.]]></resultMsg></item></root>"
    )
    fresh_post_response.raise_for_status.return_value = None
    fresh_session.get.return_value = fresh_init_response
    fresh_session.post.return_value = fresh_post_response

    stale_auth = AuthSession(token='stale', session=stale_session)
    fresh_auth = AuthSession(token='fresh', session=fresh_session)

    service = StudyRoomReservationService()
    params = _make_params()

    # fetch_with_retry는 실제 구현을 그대로 태우되(autospec + side_effect=원본), 호출 여부를
    # 단언한다 — reserve()가 create_session()으로 수동 재시도하는 구현이면 여기서 잡힌다.
    with (
        patch.object(SejongLibraryAuthService, '_login', side_effect=[stale_auth, fresh_auth]),
        patch.object(
            SejongLibraryAuthService, 'fetch_with_retry',
            autospec=True, side_effect=SejongLibraryAuthService.fetch_with_retry,
        ) as mock_fetch_with_retry,
    ):
        result = service.reserve(params)

    mock_fetch_with_retry.assert_called_once()
    assert result.success is True
    stale_session.get.assert_called_once()
    stale_session.post.assert_not_called()
    fresh_session.get.assert_called_once()
    fresh_session.post.assert_called_once()


def test_reserve_returns_auth_failure_result_when_still_expired_after_retry() -> None:
    """재인증에는 성공했지만 새 세션으로도 만료가 감지되면, auto_reserve()의 후보 탐색
    루프가 즉시 중단되도록 인증 실패 결과를 반환한다(placeholder 결과를 반환하지 않는다)."""
    stale_session = MagicMock()
    fresh_session = MagicMock()
    for session in (stale_session, fresh_session):
        expired_response = MagicMock()
        expired_response.url = 'https://libseat.sejong.ac.kr/login'
        expired_response.text = ''
        expired_response.raise_for_status.return_value = None
        session.get.return_value = expired_response

    stale_auth = AuthSession(token='stale', session=stale_session)
    fresh_auth = AuthSession(token='fresh', session=fresh_session)

    service = StudyRoomReservationService()
    params = _make_params()

    with (
        patch.object(SejongLibraryAuthService, '_login', side_effect=[stale_auth, fresh_auth]) as mock_login,
        patch.object(
            SejongLibraryAuthService, 'fetch_with_retry',
            autospec=True, side_effect=SejongLibraryAuthService.fetch_with_retry,
        ) as mock_fetch_with_retry,
    ):
        result = service.reserve(params)

    mock_fetch_with_retry.assert_called_once()
    assert mock_login.call_count == 2
    assert result.success is False
    assert result.result_code == _AUTH_FAILURE_CODE
    stale_session.post.assert_not_called()
    fresh_session.post.assert_not_called()
