import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.profile.models import Profile, VisitorCounter


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_profile가_이미_있으면_admin_추가_화면이_차단된다(admin_client: Client) -> None:
    Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    response = admin_client.get(reverse('admin:profile_profile_add'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_visitorcounter가_이미_있으면_admin_추가_화면이_차단된다(admin_client: Client) -> None:
    VisitorCounter.objects.create(pk=1, count=0)

    response = admin_client.get(reverse('admin:profile_visitorcounter_add'))

    assert response.status_code == 403
