from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.restaurants.models import Restaurant, RestaurantSuggestion, RestaurantTag

User = get_user_model()


@pytest.mark.django_db
def test_태그_문자열_표현은_이름이다() -> None:
    tag = RestaurantTag.objects.create(name='한식')
    assert str(tag) == '한식'


@pytest.mark.django_db
def test_대소문자만_다른_이름은_중복으로_취급된다() -> None:
    RestaurantTag.objects.create(name='Bar')
    with pytest.raises(ValidationError):
        RestaurantTag.objects.create(name='bar')


@pytest.mark.django_db
def test_맛집_문자열_표현은_상호명이다() -> None:
    restaurant = Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'),
    )
    assert str(restaurant) == '몽탄'


@pytest.mark.django_db
def test_기본_식사시간대는_상시이다() -> None:
    restaurant = Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'),
    )
    assert restaurant.meal_time == Restaurant.MealTime.ALL_DAY


@pytest.mark.django_db
def test_태그를_여러_개_연결할_수_있다() -> None:
    restaurant = Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'),
    )
    # slug를 명시하지 않으면 두 태그 모두 slug=''가 되어 SlugField(unique=True) 위반으로
    # IntegrityError가 난다(RestaurantTag.save()는 clean()만 호출하고 slug는 자동 생성하지
    # 않는다 — slug 자동 생성은 Task 6의 RestaurantTagAdmin.save_model()에서만 처리한다).
    tag_date = RestaurantTag.objects.create(name='데이트', slug='date')
    tag_korean = RestaurantTag.objects.create(name='한식', slug='korean-food')
    restaurant.tags.set([tag_date, tag_korean])

    assert set(restaurant.tags.values_list('name', flat=True)) == {'데이트', '한식'}


@pytest.mark.django_db
def test_개인평점은_1에서_5까지만_허용된다() -> None:
    restaurant = Restaurant(
        name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'),
        personal_rating=6,
    )
    with pytest.raises(ValidationError):
        restaurant.full_clean()


@pytest.mark.django_db
def test_제보_문자열_표현은_상호명과_제보자다() -> None:
    user = User.objects.create_user(username='visitor')
    suggestion = RestaurantSuggestion.objects.create(restaurant_name='몽탄', submitted_by=user)
    assert str(suggestion) == f'몽탄 ({user})'


@pytest.mark.django_db
def test_제보는_기본적으로_검토되지_않은_상태다() -> None:
    user = User.objects.create_user(username='visitor')
    suggestion = RestaurantSuggestion.objects.create(restaurant_name='몽탄', submitted_by=user)
    assert suggestion.is_reviewed is False
