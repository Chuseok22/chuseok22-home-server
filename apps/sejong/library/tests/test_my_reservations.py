from pathlib import Path
from unittest.mock import MagicMock

from apps.sejong.library.services.my_reservations import (
    MyReservationItem,
    MyReservationsService,
    _parse_my_seat_html,
)

_FIXTURE_HTML = (Path(__file__).parent / 'fixtures' / 'my_seat_sample.html').read_text(encoding='utf-8')


def test_parse_my_seat_html_maps_tabs_to_fixed_categories():
    items = _parse_my_seat_html(_FIXTURE_HTML)

    categories = {item.category for item in items}
    assert categories == {'열람실', '스터디룸', 'S-Lounge'}  # 시네마룸 탭은 이번 fixture에서 비어 있음


def test_parse_my_seat_html_marks_confirm_class_as_inactive():
    items = _parse_my_seat_html(_FIXTURE_HTML)
    reading_room_item = next(item for item in items if item.category == '열람실')

    assert reading_room_item.status_text == '사용완료'
    assert reading_room_item.is_active is False
    assert reading_room_item.reservation_no is None


def test_parse_my_seat_html_marks_non_confirm_as_active_with_reservation_no():
    items = _parse_my_seat_html(_FIXTURE_HTML)
    active_item = next(item for item in items if item.category == '스터디룸' and item.is_active)

    assert active_item.status_text == '취소'
    assert active_item.reservation_no == '202609030818000001'
    assert active_item.room_name == 'S1층 08스터디룸'


def test_fetch_all_returns_empty_list_when_token_missing():
    service = MyReservationsService()
    service._auth = MagicMock()
    service._auth.create_session.return_value = None

    assert service.fetch_all() == []


def test_parse_my_seat_html_returns_none_when_tab_count_unexpected():
    # tab-content가 4개가 아니면(마크업 개편 등) 빈 리스트가 아니라 None을 반환해
    # "예약 없음"과 "파싱 실패"를 구분할 수 있어야 한다.
    assert _parse_my_seat_html('<div class="tab-content"></div>') is None
