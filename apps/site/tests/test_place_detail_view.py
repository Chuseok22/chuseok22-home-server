from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from apps.engagement.models import Like
from apps.places.models import Place

User = get_user_model()


@pytest.mark.django_db
def test_장소_상세_페이지는_상호명과_한줄평을_보여준다() -> None:
    place = Place.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), personal_review='숯불향이 예술',
    )

    client = Client()
    response = client.get(reverse('site:place-detail', kwargs={'pk': place.pk}))
    body = response.content.decode()

    assert response.status_code == 200
    assert '몽탄' in body
    assert '숯불향이 예술' in body


@pytest.mark.django_db
def test_존재하지_않는_장소는_404() -> None:
    client = Client()
    response = client.get(reverse('site:place-detail', kwargs={'pk': 999999}))
    assert response.status_code == 404


@pytest.mark.django_db
@patch('apps.notifications.services.telegram.TelegramService.send_admin_alert', return_value=True)
def test_로그인_사용자에게_좋아요_버튼이_보인다(mock_send_admin_alert: MagicMock) -> None:
    user = User.objects.create_user(username='reader')
    place = Place.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))
    content_type = ContentType.objects.get_for_model(Place)
    Like.objects.create(content_type=content_type, object_id=place.pk, user=user)

    client = Client()
    client.force_login(user)
    response = client.get(reverse('site:place-detail', kwargs={'pk': place.pk}))
    body = response.content.decode()

    assert 'id="like-button"' in body
    assert '❤️ 1' in body
