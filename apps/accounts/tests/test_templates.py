import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_로그아웃_확인_페이지는_사이트_공통_레이아웃을_사용한다() -> None:
    user = get_user_model().objects.create_user(username='logout-tester', password='test-pass-1234!')
    client = Client()
    client.force_login(user)

    response = client.get(reverse('account_logout'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'css/dist/styles.css' in content
    assert 'chuseok22' in content


@pytest.mark.django_db
def test_GitHub_로그인_확인_페이지는_사이트_공통_레이아웃을_사용한다() -> None:
    client = Client()

    response = client.get(reverse('github_login'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'css/dist/styles.css' in content
    assert 'chuseok22' in content


@pytest.mark.django_db
def test_로그아웃_확인_페이지의_제출_버튼은_사이트_버튼_스타일을_사용한다() -> None:
    user = get_user_model().objects.create_user(username='logout-style-tester', password='test-pass-1234!')
    client = Client()
    client.force_login(user)

    response = client.get(reverse('account_logout'))
    content = response.content.decode()

    assert 'btn btn-primary' in content


@pytest.mark.django_db
def test_GitHub_로그인_확인_페이지의_제출_버튼은_사이트_버튼_스타일을_사용한다() -> None:
    client = Client()

    response = client.get(reverse('github_login'))
    content = response.content.decode()

    assert 'btn btn-primary' in content
