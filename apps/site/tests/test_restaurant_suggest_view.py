import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.restaurants.models import RestaurantSuggestion

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_비로그인_사용자는_제보_폼_대신_로그인_안내를_본다() -> None:
    client = Client()
    response = client.get(reverse('site:restaurant-suggest'))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'GitHub 로그인' in body


@pytest.mark.django_db
def test_로그인_사용자는_맛집을_제보할_수_있다() -> None:
    user = User.objects.create_user(username='visitor')
    client = Client()
    client.force_login(user)

    response = client.post(reverse('site:restaurant-suggest'), {
        'restaurant_name': '몽탄',
        'kakao_place_url': 'http://place.map.kakao.com/1',
        'message': '숯불구이가 맛있어요',
    })

    assert response.status_code == 200
    suggestion = RestaurantSuggestion.objects.get(restaurant_name='몽탄')
    assert suggestion.submitted_by == user
    assert suggestion.is_reviewed is False
    assert '제보해주셔서 감사합니다' in response.content.decode()


@pytest.mark.django_db
def test_상호명_없이는_제보할_수_없다() -> None:
    user = User.objects.create_user(username='visitor')
    client = Client()
    client.force_login(user)

    response = client.post(reverse('site:restaurant-suggest'), {'restaurant_name': ''})

    assert response.status_code == 200
    assert RestaurantSuggestion.objects.count() == 0


@pytest.mark.django_db
def test_분당_5회_초과시_429를_반환한다() -> None:
    user = User.objects.create_user(username='visitor')
    client = Client()
    client.force_login(user)

    for i in range(5):
        response = client.post(reverse('site:restaurant-suggest'), {'restaurant_name': f'맛집{i}'})
        assert response.status_code == 200

    sixth_response = client.post(reverse('site:restaurant-suggest'), {'restaurant_name': '여섯번째'})

    assert sixth_response.status_code == 429
    assert RestaurantSuggestion.objects.count() == 5
