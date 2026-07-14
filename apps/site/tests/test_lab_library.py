from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_비로그인_사용자는_403() -> None:
    client = Client()
    response = client.get(reverse('site:lab-library'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_is_staff_아닌_로그인_사용자는_403() -> None:
    user = User.objects.create_user(username='guest', is_staff=False)
    client = Client()
    client.force_login(user)

    response = client.get(reverse('site:lab-library'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_소유자는_예약_페이지_접근_가능() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library'))

    assert response.status_code == 200


@pytest.mark.django_db
def test_소유자는_스터디룸_가용현황_조회_가능() -> None:
    from apps.sejong.library.services.study_room import RoomSlot, StudyRoom

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_rooms = [StudyRoom(
        room_name='04스터디룸', group_title='그룹', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(RoomSlot(
            time_label='09:00', is_available=True, room_no='4', room_name='04스터디룸',
            start_time='0900', room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        ),),
    )]

    with patch('apps.site.views.StudyRoomService.fetch_all_rooms', return_value=fake_rooms):
        response = client.get(reverse('site:lab-library-rooms'), {'reserve_date': '20260705'})

    assert response.status_code == 200
    assert '04스터디룸' in response.content.decode()


@pytest.mark.django_db
def test_잘못된_날짜형식은_200으로_에러메시지_반환() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library-rooms'), {'reserve_date': 'not-a-date'})

    assert response.status_code == 200  # htmx가 swap하려면 2xx여야 함
    assert '날짜 형식이 올바르지 않습니다' in response.content.decode()


@pytest.mark.django_db
def test_소유자는_슬롯_선택시_예약폼을_받는다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library-reserve-form'), {
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6,
        'sroom_title': '그룹스터디룸6인실', 'room_name': '04스터디룸', 'seq': '0',
        'reserve_date': '20260705', 'start_time': '0900',
    })

    assert response.status_code == 200
    assert 'name="attendees_raw"' in response.content.decode()


@pytest.mark.django_db
def test_스터디룸_예약_요청_성공() -> None:
    from apps.sejong.library.services.study_room_reservation import ReservationResult

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_result = ReservationResult(
        success=True, result_code='0', result_message='예약이 완료되었습니다.',
        room_no='4', room_name='04스터디룸',
    )

    with patch('apps.site.views.StudyRoomReservationService.reserve', return_value=fake_result):
        response = client.post(reverse('site:lab-library-reserve'), {
            'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6,
            'sroom_title': '그룹스터디룸6인실', 'room_name': '04스터디룸', 'seq': '0',
            'reserve_date': '20260705', 'start_time': '0900', 'use_time': 60,
            'attendees_raw': '22011315-백지훈',
        })

    assert response.status_code == 200
    assert '예약이 완료되었습니다' in response.content.decode()


@pytest.mark.django_db
def test_예약_입력값_누락시_200으로_에러메시지_반환() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('site:lab-library-reserve'), {'room_no': '4'})  # 나머지 필드 누락

    assert response.status_code == 200  # htmx가 swap하려면 2xx여야 함
    assert '입력 오류' in response.content.decode()


@pytest.mark.django_db
def test_예약_페이지는_조회_스켈레톤과_비활성화_속성을_포함한다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library'))
    body = response.content.decode()

    assert 'hx-indicator="#rooms-skeleton"' in body
    assert 'id="rooms-skeleton"' in body
    assert 'hx-disabled-elt="find button"' in body
    assert 'id="rooms" aria-live="polite"' in body


@pytest.mark.django_db
def test_스터디룸_슬롯_버튼은_요청_중_비활성화된다() -> None:
    from apps.sejong.library.services.study_room import RoomSlot, StudyRoom

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_rooms = [StudyRoom(
        room_name='04스터디룸', group_title='그룹', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(RoomSlot(
            time_label='09:00', is_available=True, room_no='4', room_name='04스터디룸',
            start_time='0900', room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        ),),
    )]

    with patch('apps.site.views.StudyRoomService.fetch_all_rooms', return_value=fake_rooms):
        response = client.get(reverse('site:lab-library-rooms'), {'reserve_date': '20260705'})

    assert 'hx-disabled-elt="this"' in response.content.decode()


@pytest.mark.django_db
def test_예약_폼은_제출_버튼_비활성화_속성과_스피너를_포함한다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library-reserve-form'), {
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6,
        'sroom_title': '그룹스터디룸6인실', 'room_name': '04스터디룸', 'seq': '0',
        'reserve_date': '20260705', 'start_time': '0900',
    })
    body = response.content.decode()

    assert 'hx-disabled-elt="find button"' in body
    assert 'loading-spinner' in body
