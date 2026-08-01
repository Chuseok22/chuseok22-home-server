import importlib
from decimal import Decimal
from typing import Callable

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

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
def test_위도는_영90에서_90까지만_허용된다() -> None:
    restaurant = Restaurant(name='몽탄', latitude=Decimal('91'), longitude=Decimal('127'))
    with pytest.raises(ValidationError):
        restaurant.full_clean()


@pytest.mark.django_db
def test_경도는_영180에서_180까지만_허용된다() -> None:
    restaurant = Restaurant(name='몽탄', latitude=Decimal('37'), longitude=Decimal('181'))
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


@pytest.mark.django_db
def test_카테고리_기본값은_맛집이다() -> None:
    restaurant = Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'),
    )
    assert restaurant.category == Restaurant.Category.RESTAURANT


@pytest.mark.django_db
def test_카카오_장소_ID는_중복될_수_없다() -> None:
    Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), kakao_place_id='1273083863',
    )
    with pytest.raises(IntegrityError):
        Restaurant.objects.create(
            name='다른곳', latitude=Decimal('37.55'), longitude=Decimal('127.08'), kakao_place_id='1273083863',
        )


def _load_backfill_function() -> Callable[..., None]:
    module = importlib.import_module(
        'apps.restaurants.migrations.0005_add_category_and_kakao_place_id',
    )
    return module.backfill_kakao_place_id


@pytest.mark.django_db
def test_백필은_중복되는_URL을_건너뛴다() -> None:
    from django.apps import apps as django_apps

    Restaurant.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'),
        kakao_place_url='http://place.map.kakao.com/111',
    )
    Restaurant.objects.create(
        name='몽탄(중복)', latitude=Decimal('37.55'), longitude=Decimal('127.08'),
        kakao_place_url='http://place.map.kakao.com/111',
    )

    backfill = _load_backfill_function()
    backfill(django_apps, None)

    assert Restaurant.objects.filter(kakao_place_id='111').count() == 1


@pytest.mark.django_db
def test_백필은_숫자가_아닌_경로는_건너뛴다() -> None:
    from django.apps import apps as django_apps

    restaurant = Restaurant.objects.create(
        name='구형태URL', latitude=Decimal('37.54'), longitude=Decimal('127.07'),
        kakao_place_url='http://map.kakao.com/link/map/몽탄,37.54,127.07',
    )

    backfill = _load_backfill_function()
    backfill(django_apps, None)

    restaurant.refresh_from_db()
    assert restaurant.kakao_place_id is None
