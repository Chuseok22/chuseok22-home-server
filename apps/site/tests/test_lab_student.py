from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_비로그인_사용자는_403() -> None:
    client = Client()
    response = client.get(reverse('site:lab-student'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_소유자는_이름으로_학생_검색() -> None:
    from apps.sejong.student.services.student_search import StudentInfo

    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    fake_result = [StudentInfo(
        student_no='22011315', name='백지훈', dept_cd='01',
        dept_name='컴퓨터공학과', email=None, double_dept_name=None,
    )]

    with patch(
        'apps.site.views.StudentSearchService.search_by_name',
        return_value=fake_result,
    ):
        response = client.get(reverse('site:lab-student-search'), {'name': '백지훈'})

    assert response.status_code == 200
    assert '백지훈' in response.content.decode()


@pytest.mark.django_db
def test_이름과_학번_둘다_입력하면_200으로_에러메시지_반환() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-student-search'), {'name': '백지훈', 'student_no': '22011315'})

    assert response.status_code == 200  # htmx가 swap하려면 2xx여야 함
    assert '이름 또는 학번 중 하나만' in response.content.decode()


@pytest.mark.django_db
def test_외부_서비스_장애시_200으로_에러메시지_반환() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    with patch('apps.site.views.StudentSearchService.search_by_name', return_value=None):
        response = client.get(reverse('site:lab-student-search'), {'name': '백지훈'})

    assert response.status_code == 200  # htmx가 swap하려면 2xx여야 함
    assert '연결할 수 없습니다' in response.content.decode()
