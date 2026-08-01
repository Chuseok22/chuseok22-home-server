from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.places.models import Place, PlaceTag


@pytest.mark.django_db
def test_장소_목록_페이지는_등록된_장소를_모두_보여준다() -> None:
    Place.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))
    Place.objects.create(name='연남서식당', latitude=Decimal('37.56'), longitude=Decimal('126.92'))

    client = Client()
    response = client.get(reverse('site:places'))

    assert response.status_code == 200
    assert '몽탄' in response.content.decode()
    assert '연남서식당' in response.content.decode()


@pytest.mark.django_db
def test_카테고리로_필터링할_수_있다() -> None:
    Place.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), category=Place.Category.RESTAURANT,
    )
    Place.objects.create(
        name='어니언', latitude=Decimal('37.55'), longitude=Decimal('126.93'), category=Place.Category.CAFE,
    )

    client = Client()
    response = client.get(reverse('site:places'), {'category': 'restaurant'})
    body = response.content.decode()

    assert '몽탄' in body
    assert '어니언' not in body


@pytest.mark.django_db
def test_태그로_필터링할_수_있다() -> None:
    date_tag = PlaceTag.objects.create(name='데이트', slug='date')
    place_with_tag = Place.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))
    place_with_tag.tags.add(date_tag)
    Place.objects.create(name='연남서식당', latitude=Decimal('37.56'), longitude=Decimal('126.92'))

    client = Client()
    response = client.get(reverse('site:places'), {'tags': date_tag.id})
    body = response.content.decode()

    assert '몽탄' in body
    assert '연남서식당' not in body


@pytest.mark.django_db
def test_태그와_카테고리_필터를_동시에_적용할_수_있다() -> None:
    date_tag = PlaceTag.objects.create(name='데이트', slug='date')
    matching = Place.objects.create(
        name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'), category=Place.Category.RESTAURANT,
    )
    matching.tags.add(date_tag)
    wrong_category = Place.objects.create(
        name='어니언', latitude=Decimal('37.55'), longitude=Decimal('126.93'), category=Place.Category.CAFE,
    )
    wrong_category.tags.add(date_tag)
    Place.objects.create(
        name='연남서식당', latitude=Decimal('37.56'), longitude=Decimal('126.92'), category=Place.Category.RESTAURANT,
    )

    client = Client()
    response = client.get(reverse('site:places'), {'tags': date_tag.id, 'category': 'restaurant'})
    body = response.content.decode()

    assert '몽탄' in body
    assert '어니언' not in body
    assert '연남서식당' not in body


@pytest.mark.django_db
def test_태그_필터_링크는_현재_카테고리_선택을_유지한다() -> None:
    tag = PlaceTag.objects.create(name='데이트', slug='date')
    Place.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))

    client = Client()
    response = client.get(reverse('site:places'), {'category': 'restaurant'})
    body = response.content.decode()

    assert f'tags={tag.id}&amp;category=restaurant' in body


@pytest.mark.django_db
def test_htmx_요청은_프래그먼트만_반환한다() -> None:
    Place.objects.create(name='몽탄', latitude=Decimal('37.54'), longitude=Decimal('127.07'))

    client = Client()
    response = client.get(reverse('site:places'), HTTP_HX_REQUEST='true')
    body = response.content.decode()

    assert '<html' not in body
    assert '몽탄' in body


@pytest.mark.django_db
def test_31번째_장소부터는_다음_페이지에_보인다() -> None:
    for i in range(31):
        Place.objects.create(name=f'장소{i:02d}', latitude=Decimal('37.5'), longitude=Decimal('127.0'))

    client = Client()
    first_page = client.get(reverse('site:places')).content.decode()
    second_page = client.get(reverse('site:places'), {'page': 2}).content.decode()

    # Place.Meta.ordering이 ['-created_at']이라 가장 먼저 만든 '장소00'이 목록의 31번째로 밀린다.
    assert '장소00' not in first_page
    assert '장소00' in second_page


@pytest.mark.django_db
def test_31번째_장소가_있으면_페이지네이션_링크가_보인다() -> None:
    for i in range(31):
        Place.objects.create(name=f'장소{i:02d}', latitude=Decimal('37.5'), longitude=Decimal('127.0'))

    client = Client()
    body = client.get(reverse('site:places')).content.decode()

    assert '다음' in body
