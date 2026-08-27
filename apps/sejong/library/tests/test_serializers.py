from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_study_room_reserve_rejects_attendee_count_below_half_capacity() -> None:
    # 검증이 실수로 통과하더라도 실제 외부 API(sroomReserveMain.php)를 호출하지 않도록 방어적으로
    # patch한다 — 이 테스트의 목적은 400에서 걸러지는지 확인하는 것이고, reserve() 호출 자체가
    # 일어나면 안 된다(호출되면 아래 patch가 있어도 진짜 네트워크를 타지 않게만 막아준다).
    user = User.objects.create_user(username='testuser')
    client = APIClient()
    client.force_authenticate(user)

    with patch('apps.sejong.library.views.StudyRoomReservationService.reserve') as mock_reserve:
        response = client.post('/api/v1/library/study-rooms/reserve/', {
            'room_no': '4', 'room_gb': 'S1', 'seat_cnt': 6, 'sroom_title': '그룹스터디룸6인실',
            'room_name': '04스터디룸', 'seq': '0', 'reserve_date': '20260901', 'start_time': '1400',
            'use_time': 60, 'attendees': [{'student_id': '22011315', 'name': '백지훈'}],
        }, format='json')

    assert response.status_code == 400
    assert '정원(6명)의 절반 이상인 최소 3명' in str(response.data)
    mock_reserve.assert_not_called()
