from unittest.mock import MagicMock, patch

from apps.sejong.library.services.slounge import Lounge, LoungeSlot, SloungeService, _LOUNGE_GROUPS

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


def test_lounge_groups_cover_all_six_known_groups():
    assert len(_LOUNGE_GROUPS) == 6
    titles = {(g['sroomTitle'], g['seatCnt']) for g in _LOUNGE_GROUPS}
    assert titles == {('S-Lounge 6인석', 6), ('S-Loung 4인석', 4)}
    assert all(g['roomGB'] == 'S3' for g in _LOUNGE_GROUPS)


def test_fetch_all_lounges_returns_empty_list_when_token_missing():
    service = SloungeService()
    service._auth = MagicMock()
    service._auth.fetch_token.return_value = None

    assert service.fetch_all_lounges('20260901') == []


@patch('apps.sejong.library.services.slounge.requests.Session')
def test_fetch_all_lounges_parses_all_groups(mock_session_cls):
    mock_response = MagicMock()
    mock_response.text = _SAMPLE_HTML
    mock_response.url = 'https://libseat.sejong.ac.kr/mobile/MA/loungeMap.php'
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls.return_value = mock_session

    service = SloungeService()
    service._auth = MagicMock()
    service._auth.fetch_token.return_value = 'test-token'

    lounges = service.fetch_all_lounges('20260901')

    assert len(lounges) == len(_LOUNGE_GROUPS)
    assert all(isinstance(lounge, Lounge) for lounge in lounges)
    assert lounges[0].room_name == 'SL1'
    assert lounges[0].slots[0] == LoungeSlot(time_label='09:00', is_available=False)
