from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.restaurants.models import Restaurant, RestaurantTag


@pytest.mark.django_db
def test_맛집_목록_페이지는_등록된_맛집을_모두_보여준다() -> None:
    Restaurant.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))
    Restaurant.objects.create(name='연남서식당', latitude=Decimal('37.56'), longitude=Decimal('126.92'))

    client = Client()
    response = client.get(reverse('site:restaurants'))

    assert response.status_code == 200
    assert '몽탄' in response.content.decode()
    assert '연남서식당' in response.content.decode()


@pytest.mark.django_db
def test_식사시간대로_필터링할_수_있다() -> None:
    Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'),
        meal_time=Restaurant.MealTime.DINNER,
    )
    Restaurant.objects.create(
        name='이삭토스트', latitude=Decimal('37.55'), longitude=Decimal('126.93'),
        meal_time=Restaurant.MealTime.BREAKFAST,
    )

    client = Client()
    response = client.get(reverse('site:restaurants'), {'meal_time': 'dinner'})
    body = response.content.decode()

    assert '몽탄' in body
    assert '이삭토스트' not in body


@pytest.mark.django_db
def test_태그로_필터링할_수_있다() -> None:
    date_tag = RestaurantTag.objects.create(name='데이트', slug='date')
    restaurant_with_tag = Restaurant.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))
    restaurant_with_tag.tags.add(date_tag)
    Restaurant.objects.create(name='연남서식당', latitude=Decimal('37.56'), longitude=Decimal('126.92'))

    client = Client()
    response = client.get(reverse('site:restaurants'), {'tags': date_tag.id})
    body = response.content.decode()

    assert '몽탄' in body
    assert '연남서식당' not in body


@pytest.mark.django_db
def test_태그와_식사시간대_필터를_동시에_적용할_수_있다() -> None:
    date_tag = RestaurantTag.objects.create(name='데이트', slug='date')
    matching = Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'),
        meal_time=Restaurant.MealTime.DINNER,
    )
    matching.tags.add(date_tag)
    # 태그는 같지만 식사시간대가 다른 곳, 식사시간대는 같지만 태그가 없는 곳 모두 제외되어야 한다
    wrong_meal_time = Restaurant.objects.create(
        name='이삭토스트', latitude=Decimal('37.55'), longitude=Decimal('126.93'),
        meal_time=Restaurant.MealTime.BREAKFAST,
    )
    wrong_meal_time.tags.add(date_tag)
    Restaurant.objects.create(
        name='연남서식당', latitude=Decimal('37.56'), longitude=Decimal('126.92'),
        meal_time=Restaurant.MealTime.DINNER,
    )

    client = Client()
    response = client.get(reverse('site:restaurants'), {'tags': date_tag.id, 'meal_time': 'dinner'})
    body = response.content.decode()

    assert '몽탄' in body
    assert '이삭토스트' not in body
    assert '연남서식당' not in body


@pytest.mark.django_db
def test_태그_필터_링크는_현재_식사시간대_선택을_유지한다() -> None:
    tag = RestaurantTag.objects.create(name='데이트', slug='date')
    Restaurant.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))

    client = Client()
    response = client.get(reverse('site:restaurants'), {'meal_time': 'dinner'})
    body = response.content.decode()

    # 태그 링크를 클릭해도 현재 선택된 meal_time=dinner가 querystring에 함께 남아있어야 한다
    assert f'tags={tag.id}&amp;meal_time=dinner' in body


@pytest.mark.django_db
def test_htmx_요청은_프래그먼트만_반환한다() -> None:
    Restaurant.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))

    client = Client()
    response = client.get(reverse('site:restaurants'), HTTP_HX_REQUEST='true')
    body = response.content.decode()

    assert '<html' not in body
    assert '몽탄' in body
