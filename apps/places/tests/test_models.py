from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.places.models import Place, PlaceSuggestion, PlaceTag

User = get_user_model()


@pytest.mark.django_db
def test_태그_문자열_표현은_이름이다() -> None:
    tag = PlaceTag.objects.create(name='한식')
    assert str(tag) == '한식'


@pytest.mark.django_db
def test_대소문자만_다른_이름은_중복으로_취급된다() -> None:
    PlaceTag.objects.create(name='Bar')
    with pytest.raises(ValidationError):
        PlaceTag.objects.create(name='bar')


@pytest.mark.django_db
def test_장소_문자열_표현은_상호명이다() -> None:
    place = Place.objects.create(name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'))
    assert str(place) == '몽탄'


@pytest.mark.django_db
def test_기본_카테고리는_맛집이다() -> None:
    place = Place.objects.create(name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'))
    assert place.category == Place.Category.RESTAURANT


@pytest.mark.django_db
def test_기본_식사시간대는_상시이다() -> None:
    place = Place.objects.create(name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'))
    assert place.meal_time == Place.MealTime.ALL_DAY


@pytest.mark.django_db
def test_카카오_장소_ID는_중복될_수_없다() -> None:
    Place.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), kakao_place_id='1')
    with pytest.raises(IntegrityError):
        Place.objects.create(name='다른곳', latitude=Decimal('37.55'), longitude=Decimal('127.08'), kakao_place_id='1')


@pytest.mark.django_db
def test_태그를_여러_개_연결할_수_있다() -> None:
    place = Place.objects.create(name='몽탄', latitude=Decimal('37.540000'), longitude=Decimal('127.070000'))
    # slug를 명시하지 않으면 두 태그 모두 slug=''가 되어 SlugField(unique=True) 위반이다
    # (PlaceTag.save()는 clean()만 호출하고, slug 자동 생성은 PlaceTagAdmin.save_model()에서만 처리한다).
    tag_date = PlaceTag.objects.create(name='데이트', slug='date')
    tag_korean = PlaceTag.objects.create(name='한식', slug='korean-food')
    place.tags.set([tag_date, tag_korean])
    assert set(place.tags.values_list('name', flat=True)) == {'데이트', '한식'}


@pytest.mark.django_db
def test_개인평점은_1에서_5까지만_허용된다() -> None:
    place = Place(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), personal_rating=6)
    with pytest.raises(ValidationError):
        place.full_clean()


@pytest.mark.django_db
def test_위도는_영90에서_90까지만_허용된다() -> None:
    place = Place(name='몽탄', latitude=Decimal('91'), longitude=Decimal('127'))
    with pytest.raises(ValidationError):
        place.full_clean()


@pytest.mark.django_db
def test_경도는_영180에서_180까지만_허용된다() -> None:
    place = Place(name='몽탄', latitude=Decimal('37'), longitude=Decimal('181'))
    with pytest.raises(ValidationError):
        place.full_clean()


@pytest.mark.django_db
def test_제보_문자열_표현은_상호명과_제보자다() -> None:
    user = User.objects.create_user(username='visitor')
    suggestion = PlaceSuggestion.objects.create(restaurant_name='몽탄', submitted_by=user)
    assert str(suggestion) == f'몽탄 ({user})'


@pytest.mark.django_db
def test_제보는_기본적으로_검토되지_않은_상태다() -> None:
    user = User.objects.create_user(username='visitor')
    suggestion = PlaceSuggestion.objects.create(restaurant_name='몽탄', submitted_by=user)
    assert suggestion.is_reviewed is False
