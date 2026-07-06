import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_미인증_사용자는_로그인_페이지로_리다이렉트() -> None:
    client = Client()
    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 302
    assert response.url.startswith('/accounts/login/')


@pytest.mark.django_db
def test_비staff_사용자는_403() -> None:
    user = User.objects.create_user(username='reader', is_staff=False)
    client = Client()
    client.force_login(user)

    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_사용자는_대시보드_접근_가능() -> None:
    user = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(user)

    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 200
