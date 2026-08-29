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
def test_소유자는_스터디룸_가용현황을_매트릭스로_조회_가능() -> None:
    from apps.sejong.library.services.study_room import RoomSlot, StudyRoom

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_rooms = [StudyRoom(
        room_name='04스터디룸', group_title='그룹', seat_cnt=6,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
        slots=(
            RoomSlot(
                time_label='09:00', is_available=True, room_no='4', room_name='04스터디룸',
                start_time='0900', room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0',
            ),
            RoomSlot(time_label='10:00', is_available=False),
        ),
    )]

    with patch('apps.site.views.StudyRoomService.fetch_all_rooms', return_value=fake_rooms):
        response = client.get(reverse('site:lab-library-rooms'), {'reserve_date': '20260705'})

    body = response.content.decode()
    assert response.status_code == 200
    assert '04스터디룸' in body
    assert '<table' in body
    assert '09:00' in body  # 헤더 컬럼
    assert '마감' in body  # 예약 불가 셀


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
            'attendees_raw': '22011315-백지훈,22011316-김철수,22011317-이영희',
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
    assert 'hx-disabled-elt="this"' in body
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


@pytest.mark.django_db
def test_library_reserve_form_rejects_attendee_count_below_half_capacity() -> None:
    from apps.site.forms import LibraryReserveForm

    form = LibraryReserveForm(data={
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6, 'sroom_title': '그룹스터디룸6인실',
        'room_name': '04스터디룸', 'seq': '0', 'reserve_date': '20260901', 'start_time': '1400',
        'use_time': 60, 'attendees_raw': '22011315-백지훈',
    })

    assert not form.is_valid()
    assert '정원(6명)의 절반 이상인 최소 3명' in str(form.errors)


@pytest.mark.django_db
def test_library_reserve_form_accepts_attendee_count_at_half_capacity() -> None:
    from apps.site.forms import LibraryReserveForm

    form = LibraryReserveForm(data={
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6, 'sroom_title': '그룹스터디룸6인실',
        'room_name': '04스터디룸', 'seq': '0', 'reserve_date': '20260901', 'start_time': '1400',
        'use_time': 60, 'attendees_raw': '22011315-백지훈,22011316-김철수,22011317-이영희',
    })

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_소유자는_S_Lounge_가용현황_조회_가능() -> None:
    from apps.sejong.library.services.slounge import Lounge, LoungeSlot

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_lounges = [Lounge(
        room_name='SL1', group_title='S-Lounge 6인석', seat_cnt=6,
        room_gb='S3', sroom_title='S-Lounge 6인석', seq='0',
        slots=(LoungeSlot(time_label='09:00', is_available=False),),
    )]

    with patch('apps.site.views.SloungeService.fetch_all_lounges', return_value=fake_lounges):
        response = client.get(
            reverse('site:lab-library-rooms'),
            {'reserve_date': '20260901', 'room_type': 's_lounge'},
        )

    assert response.status_code == 200
    assert 'SL1' in response.content.decode()


@pytest.mark.django_db
def test_소유자는_내_예약_목록을_실데이터로_조회() -> None:
    from apps.sejong.library.services.my_reservations import MyReservationItem

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_item = MyReservationItem(
        category='스터디룸', date='2026.09.03', time_range='18:00 ~ 20:00',
        room_name='S1층 08스터디룸', status_text='취소', is_active=True,
        reservation_no='202609030818000001',
    )

    with patch('apps.site.views.MyReservationsService.fetch_all', return_value=[fake_item]):
        response = client.get(reverse('site:lab-library-my-reservations'))

    assert response.status_code == 200
    assert 'S1층 08스터디룸' in response.content.decode()


@pytest.mark.django_db
def test_내_예약_목록_조회_실패_시_빈_목록이_아닌_503_반환() -> None:
    # fetch_all()이 None(인증/네트워크/마크업 실패)을 반환하면 "예약 없음"으로 오인되지 않도록
    # 별도 실패 상태와 503을 반환해야 한다.
    owner = User.objects.create_user(username='owner-fetch-fail', is_staff=True)
    client = Client()
    client.force_login(owner)

    with patch('apps.site.views.MyReservationsService.fetch_all', return_value=None):
        response = client.get(reverse('site:lab-library-my-reservations'))

    assert response.status_code == 503
    assert '예약 내역이 없습니다' not in response.content.decode()


@pytest.mark.django_db
def test_내_예약_목록_조회_시_자격증명_누락이면_503_반환() -> None:
    owner = User.objects.create_user(username='owner-no-creds', is_staff=True)
    client = Client()
    client.force_login(owner)

    with patch(
        'apps.site.views.MyReservationsService.fetch_all',
        side_effect=ValueError('SEJONG_STUDENT_ID 또는 SEJONG_PASSWORD가 설정되지 않았습니다.'),
    ):
        response = client.get(reverse('site:lab-library-my-reservations'))

    assert response.status_code == 503


@pytest.mark.django_db
def test_스터디룸_예약_성공시_참여자_이름이_최신값으로_갱신() -> None:
    from apps.sejong.library.models import ReservationAttendee
    from apps.sejong.library.services.study_room_reservation import ReservationResult

    ReservationAttendee.objects.create(student_id='22011315', name='오타이름')

    owner = User.objects.create_user(username='owner-upsert', is_staff=True)
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
            'attendees_raw': '22011315-백지훈,22011316-김철수,22011317-이영희',
        })

    assert response.status_code == 200
    assert ReservationAttendee.objects.get(student_id='22011315').name == '백지훈'


@pytest.mark.django_db
def test_소유자는_저장된_참여자를_삭제할_수_있다() -> None:
    from apps.sejong.library.models import ReservationAttendee

    attendee = ReservationAttendee.objects.create(student_id='22011315', name='백지훈')
    owner = User.objects.create_user(username='owner-delete', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.delete(
        reverse('site:lab-library-attendee-delete', kwargs={'pk': attendee.pk})
    )

    assert response.status_code == 200
    assert not ReservationAttendee.objects.filter(pk=attendee.pk).exists()


@pytest.mark.django_db
def test_비로그인_사용자는_참여자_삭제시_403() -> None:
    from apps.sejong.library.models import ReservationAttendee

    attendee = ReservationAttendee.objects.create(student_id='22011315', name='백지훈')
    client = Client()

    response = client.delete(
        reverse('site:lab-library-attendee-delete', kwargs={'pk': attendee.pk})
    )

    assert response.status_code == 403
    assert ReservationAttendee.objects.filter(pk=attendee.pk).exists()


@pytest.mark.django_db
def test_참여자_삭제_라우트에_GET_요청시_405() -> None:
    from apps.sejong.library.models import ReservationAttendee

    attendee = ReservationAttendee.objects.create(student_id='22011315', name='백지훈')
    owner = User.objects.create_user(username='owner-delete-get', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(
        reverse('site:lab-library-attendee-delete', kwargs={'pk': attendee.pk})
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_예약폼은_저장된_참여자_카탈로그를_렌더링한다() -> None:
    from apps.sejong.library.models import ReservationAttendee

    ReservationAttendee.objects.create(student_id='22011315', name='백지훈')
    owner = User.objects.create_user(username='owner-catalog', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library-reserve-form'), {
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6,
        'sroom_title': '그룹스터디룸6인실', 'room_name': '04스터디룸', 'seq': '0',
        'reserve_date': '20260705', 'start_time': '0900',
    })
    body = response.content.decode()

    assert response.status_code == 200
    assert 'id="attendee-catalog"' in body
    assert 'data-student-id="22011315"' in body
    assert 'data-name="백지훈"' in body
    assert f'hx-delete="/lab/library/attendees/{ReservationAttendee.objects.get().pk}/"' in body


@pytest.mark.django_db
def test_예약폼은_저장된_참여자가_없어도_정상_렌더링된다() -> None:
    owner = User.objects.create_user(username='owner-catalog-empty', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library-reserve-form'), {
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6,
        'sroom_title': '그룹스터디룸6인실', 'room_name': '04스터디룸', 'seq': '0',
        'reserve_date': '20260705', 'start_time': '0900',
    })

    assert response.status_code == 200
    assert 'id="attendee-catalog"' in response.content.decode()


@pytest.mark.django_db
def test_예약폼_참여자_입력행은_자동완성_드롭다운_골격을_포함한다() -> None:
    owner = User.objects.create_user(username='owner-autocomplete', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-library-reserve-form'), {
        'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6,
        'sroom_title': '그룹스터디룸6인실', 'room_name': '04스터디룸', 'seq': '0',
        'reserve_date': '20260705', 'start_time': '0900',
    })
    body = response.content.decode()

    assert response.status_code == 200
    assert 'attendee-suggestions' in body
    assert 'suggestion-item' in body
