from decimal import Decimal

import pytest
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.restaurants.models import Restaurant, RestaurantSuggestion, RestaurantTag

User = get_user_model()


def test_세_모델_모두_admin에_등록되어_있다() -> None:
    assert site.is_registered(Restaurant)
    assert site.is_registered(RestaurantTag)
    assert site.is_registered(RestaurantSuggestion)


@pytest.mark.django_db
def test_스태프는_맛집_등록_화면에_접근할_수_있다() -> None:
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    response = client.get(reverse('admin:restaurants_restaurant_add'))

    assert response.status_code == 200


@pytest.mark.django_db
def test_태그_어드민에서_슬러그가_자동_생성된다() -> None:
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    client.post(reverse('admin:restaurants_restauranttag_add'), {'name': '데이트'})

    tag = RestaurantTag.objects.get(name='데이트')
    assert tag.slug
