from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.sejong.library.services.my_reservations import (
    MyReservationItem,
    MyReservationsService,
    _parse_my_seat_html,
)

User = get_user_model()

_FIXTURE_HTML = (Path(__file__).parent / 'fixtures' / 'my_seat_sample.html').read_text(encoding='utf-8')


def test_parse_my_seat_html_maps_tabs_to_fixed_categories() -> None:
    items = _parse_my_seat_html(_FIXTURE_HTML)

    categories = {item.category for item in items}
    assert categories == {'열람실', '스터디룸', 'S-Lounge'}  # 시네마룸 탭은 이번 fixture에서 비어 있음


def test_parse_my_seat_html_marks_confirm_class_as_inactive() -> None:
    items = _parse_my_seat_html(_FIXTURE_HTML)
    reading_room_item = next(item for item in items if item.category == '열람실')

    assert reading_room_item.status_text == '사용완료'
    assert reading_room_item.is_active is False
    assert reading_room_item.reservation_no is None


def test_parse_my_seat_html_marks_non_confirm_as_active_with_reservation_no() -> None:
    items = _parse_my_seat_html(_FIXTURE_HTML)
    active_item = next(item for item in items if item.category == '스터디룸' and item.is_active)

    assert active_item.status_text == '취소'
    assert active_item.reservation_no == '202609030818000001'
    assert active_item.room_name == 'S1층 08스터디룸'


def test_fetch_all_returns_none_when_token_missing() -> None:
    service = MyReservationsService()
    service._auth = MagicMock()
    service._auth.fetch_with_retry.return_value = None

    assert service.fetch_all() is None


def test_parse_my_seat_html_returns_none_when_tab_count_unexpected() -> None:
    # tab-content가 4개가 아니면(마크업 개편 등) 빈 리스트가 아니라 None을 반환해
    # "예약 없음"과 "파싱 실패"를 구분할 수 있어야 한다.
    assert _parse_my_seat_html('<div class="tab-content"></div>') is None


@pytest.mark.django_db
def test_my_reservations_view_returns_200_with_items(monkeypatch) -> None:
    fake_item = MyReservationItem(
        category='스터디룸', date='2026.09.03', time_range='18:00 ~ 20:00',
        room_name='S1층 08스터디룸', status_text='취소', is_active=True,
        reservation_no='202609030818000001',
    )
    monkeypatch.setattr(
        'apps.sejong.library.views.MyReservationsService.fetch_all',
        lambda self: [fake_item],
    )

    user = User.objects.create_user(username='testuser', is_staff=True)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get('/api/v1/library/my-reservations/')

    assert response.status_code == 200
    assert response.data[0]['room_name'] == 'S1층 08스터디룸'


@pytest.mark.django_db
def test_my_reservations_view_returns_503_when_parsing_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        'apps.sejong.library.views.MyReservationsService.fetch_all',
        lambda self: None,
    )

    user = User.objects.create_user(username='testuser', is_staff=True)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get('/api/v1/library/my-reservations/')

    assert response.status_code == 503


@pytest.mark.django_db
def test_my_reservations_view_returns_403_for_non_staff_user(monkeypatch) -> None:
    # 조회 대상이 서버에 고정된 소유자 계정(SEJONG_STUDENT_ID)이므로,
    # 소유자가 아닌 인증 사용자에게는 접근을 허용하지 않아야 한다.
    monkeypatch.setattr(
        'apps.sejong.library.views.MyReservationsService.fetch_all',
        lambda self: [],
    )

    user = User.objects.create_user(username='non-owner', is_staff=False)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get('/api/v1/library/my-reservations/')

    assert response.status_code == 403


def test_fetch_all_delegates_to_fetch_with_retry() -> None:
    service = MyReservationsService()
    service._auth = MagicMock()
    fake_items = [
        MyReservationItem(
            category='스터디룸', date='2026.09.03', time_range='18:00 ~ 20:00',
            room_name='S1층 08스터디룸', status_text='취소', is_active=True,
            reservation_no='202609030818000001',
        ),
    ]
    service._auth.fetch_with_retry.return_value = fake_items

    result = service.fetch_all()

    assert result == fake_items
    service._auth.fetch_with_retry.assert_called_once_with(service._fetch_with_session)


def test_fetch_with_session_signals_expired_on_login_redirect() -> None:
    from apps.sejong.library.services.sejong_auth import AuthSession

    service = MyReservationsService()
    session = MagicMock()
    response = MagicMock()
    response.url = 'https://libseat.sejong.ac.kr/login'
    response.text = ''
    session.get.return_value = response
    auth_session = AuthSession(token='t', session=session)

    items, expired = service._fetch_with_session(auth_session)

    assert items is None
    assert expired is True


def test_fetch_with_session_parses_valid_response() -> None:
    from apps.sejong.library.services.sejong_auth import AuthSession

    service = MyReservationsService()
    session = MagicMock()
    response = MagicMock()
    response.url = 'https://libseat.sejong.ac.kr/mobile/MA/mySeat.php'
    response.text = _FIXTURE_HTML
    session.get.return_value = response
    auth_session = AuthSession(token='t', session=session)

    items, expired = service._fetch_with_session(auth_session)

    assert expired is False
    assert items is not None
    assert len(items) > 0
