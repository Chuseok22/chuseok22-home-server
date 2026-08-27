from apps.sejong.library.services._room_map_parser import (
    ParsedRoom,
    ParsedSlot,
    extract_url_param,
    is_session_expired,
    parse_room_map_html,
)

_SAMPLE_HTML = """
<div class="al-title">그룹스터디룸 6인실 02~04</div>
<div class="avl-slot">
    <div class="at-head"><span>시간</span></div>
    <div class="at-title"><span>02스터디룸</span></div>
    <div class="at-title"><span>03스터디룸</span></div>
</div>
<div class="avl-data-slot">
    <div class="avl-time">09:00</div>
    <div class="avl-button"><a href="?sroomNo=2&sroomName=02스터디룸&startTime=0900">예약</a></div>
    <div class="avl-button">예약불가</div>
</div>
<div class="avl-data-slot">
    <div class="avl-time">10:00</div>
    <div class="avl-button">예약불가</div>
    <div class="avl-button"><a href="?sroomNo=3&sroomName=03스터디룸&startTime=1000">예약</a></div>
</div>
"""


def test_parse_room_map_html_extracts_group_title_and_room_names():
    rooms = parse_room_map_html(_SAMPLE_HTML)

    assert [r.room_name for r in rooms] == ['02스터디룸', '03스터디룸']
    assert all(r.group_title == '그룹스터디룸 6인실 02~04' for r in rooms)


def test_parse_room_map_html_marks_available_and_booked_slots():
    rooms = parse_room_map_html(_SAMPLE_HTML)
    room_02 = next(r for r in rooms if r.room_name == '02스터디룸')

    assert room_02.slots[0] == ParsedSlot(
        time_label='09:00', is_available=True,
        room_no='2', room_name='02스터디룸', start_time='0900',
    )
    assert room_02.slots[1] == ParsedSlot(time_label='10:00', is_available=False)


def test_parse_room_map_html_returns_empty_list_when_no_slot_header():
    assert parse_room_map_html('<div class="al-title">제목만 있음</div>') == []


def test_extract_url_param_returns_none_when_missing():
    assert extract_url_param('https://example.com/x?a=1', 'b') is None


def test_extract_url_param_returns_value_when_present():
    assert extract_url_param('https://example.com/x?sroomNo=7', 'sroomNo') == '7'


class _FakeResponse:
    def __init__(self, url: str, text: str) -> None:
        self.url = url
        self.text = text


def test_is_session_expired_detects_login_redirect_url():
    assert is_session_expired(_FakeResponse('https://libseat.sejong.ac.kr/login', '')) is True


def test_is_session_expired_detects_login_body_keyword():
    assert is_session_expired(_FakeResponse('https://libseat.sejong.ac.kr/x', 'mainLogin')) is True


def test_is_session_expired_false_for_normal_response():
    assert is_session_expired(_FakeResponse('https://libseat.sejong.ac.kr/x', '<div>정상</div>')) is False
