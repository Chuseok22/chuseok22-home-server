from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from apps.engagement.models import Like
from apps.restaurants.models import Restaurant

User = get_user_model()


@pytest.mark.django_db
def test_맛집_상세_페이지는_상호명과_한줄평을_보여준다() -> None:
    restaurant = Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), personal_review='숯불향이 예술',
    )

    client = Client()
    response = client.get(reverse('site:restaurant-detail', kwargs={'pk': restaurant.pk}))
    body = response.content.decode()

    assert response.status_code == 200
    assert '몽탄' in body
    assert '숯불향이 예술' in body


@pytest.mark.django_db
def test_존재하지_않는_맛집은_404() -> None:
    client = Client()
    response = client.get(reverse('site:restaurant-detail', kwargs={'pk': 999999}))
    assert response.status_code == 404


@pytest.mark.django_db
@patch('apps.notifications.services.telegram.TelegramService.send_admin_alert', return_value=True)
def test_로그인_사용자에게_좋아요_버튼이_보인다(mock_send_admin_alert: MagicMock) -> None:
    # Like 생성은 apps.engagement.signals의 post_save 시그널로 텔레그램 관리자 알림을
    # 실제로 호출한다(apps/engagement/tests/conftest.py의 autouse mock은 apps/site/tests/에는
    # 적용되지 않으므로 이 테스트에서 직접 mock한다).
    user = User.objects.create_user(username='reader')
    restaurant = Restaurant.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))
    content_type = ContentType.objects.get_for_model(Restaurant)
    Like.objects.create(content_type=content_type, object_id=restaurant.pk, user=user)

    client = Client()
    client.force_login(user)
    response = client.get(reverse('site:restaurant-detail', kwargs={'pk': restaurant.pk}))
    body = response.content.decode()

    assert 'id="like-button"' in body
    assert '❤️ 1' in body
