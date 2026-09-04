from dataclasses import fields
from unittest.mock import MagicMock, patch

from apps.sejong.library.services.sejong_auth import AuthSession, SejongLibraryAuthService
from apps.sejong.library.services.slounge import Lounge, LoungeSlot, SloungeService, _LOUNGE_GROUPS
from apps.sejong.library.services.study_room import RoomSlot, StudyRoom

_SAMPLE_HTML = """
<div class="al-title">S-Lounge 6인석</div>
<div class="avl-slot">
    <div class="at-head"><span>시간</span></div>
    <div class="at-title"><span>SL1</span></div>
</div>
<div class="avl-data-slot">
    <div class="avl-time">09:00</div>
    <div class="avl-button">예약불가</div>
</div>
"""


def test_lounge_groups_cover_all_six_known_groups() -> None:
    assert len(_LOUNGE_GROUPS) == 6
    titles = {(g['sroomTitle'], g['seatCnt']) for g in _LOUNGE_GROUPS}
    assert titles == {('S-Lounge 6인석', 6), ('S-Loung 4인석', 4)}
    assert all(g['roomGB'] == 'S3' for g in _LOUNGE_GROUPS)


def test_fetch_all_lounges_returns_empty_list_when_token_missing() -> None:
    service = SloungeService()
    # spec=으로 존재하지 않는 속성 접근을 막고, fetch_token도 함께 None으로 고정해 — 아직 코드가
    # 옛 fetch_token() 경로를 쓰는 RED 단계에서도 진짜 requests.Session()이 만들어져 학술정보원에
    # 실제 GET을 날리는 일이 없도록 이중으로 막는다(마이그레이션 전후 모두 안전).
    service._auth = MagicMock(spec=SejongLibraryAuthService)
    service._auth.fetch_token.return_value = None
    service._auth.fetch_with_retry.return_value = None

    assert service.fetch_all_lounges('20260901') == []


@patch('apps.sejong.library.services.slounge.requests.Session')
def test_fetch_all_lounges_parses_all_groups(mock_session_cls) -> None:
    mock_response = MagicMock()
    mock_response.text = _SAMPLE_HTML
    mock_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/loungeMap.php'
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls.return_value = mock_session

    service = SloungeService()
    service._auth = MagicMock(spec=SejongLibraryAuthService)
    fake_auth_session = AuthSession(token='test-token', session=MagicMock())
    service._auth.fetch_with_retry.side_effect = (
        lambda operation: operation(fake_auth_session)[0]
    )

    lounges = service.fetch_all_lounges('20260901')

    assert len(lounges) == len(_LOUNGE_GROUPS)
    assert all(isinstance(lounge, Lounge) for lounge in lounges)
    assert lounges[0].room_name == 'SL1'
    assert lounges[0].slots[0] == LoungeSlot(time_label='09:00', is_available=False)


def test_lounge_dataclasses_match_study_room_shape_for_serializer_reuse() -> None:
    assert [f.name for f in fields(LoungeSlot)] == [f.name for f in fields(RoomSlot)]
    assert [f.name for f in fields(Lounge)] == [f.name for f in fields(StudyRoom)]
