from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.places.models import Place, PlaceSuggestion, PlaceTag
from apps.places.services.kakao import KakaoApiError, KakaoPlaceResult

User = get_user_model()


def test_세_모델_모두_admin에_등록되어_있다() -> None:
    assert site.is_registered(Place)
    assert site.is_registered(PlaceTag)
    assert site.is_registered(PlaceSuggestion)


@pytest.mark.django_db
def test_스태프는_장소_등록_화면에_접근할_수_있다() -> None:
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    response = client.get(reverse('admin:places_place_add'))

    assert response.status_code == 200


@pytest.mark.django_db
def test_태그_어드민에서_슬러그가_자동_생성된다() -> None:
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    client.post(reverse('admin:places_placetag_add'), {'name': '데이트'})

    tag = PlaceTag.objects.get(name='데이트')
    assert tag.slug


@pytest.mark.django_db
def test_비로그인_사용자는_카카오_검색_프록시에_접근할_수_없다() -> None:
    client = Client()
    response = client.get(reverse('admin:places_place_kakao_search'), {'query': '몽탄'})
    assert response.status_code in (302, 403)


@pytest.mark.django_db
@patch('apps.places.admin.search_places')
def test_스태프는_카카오_검색_결과를_JSON으로_받는다(mock_search_places: MagicMock) -> None:
    mock_search_places.return_value = [
        KakaoPlaceResult(
            name='몽탄', address='서울 성동구 성수동2가 289-13', road_address='서울 성동구 서울숲2길 32-14',
            latitude=37.5445037, longitude=127.0442254, category='음식점 > 한식', place_url='http://place.map.kakao.com/1',
        )
    ]
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    response = client.get(reverse('admin:places_place_kakao_search'), {'query': '몽탄'})

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['results'][0]['name'] == '몽탄'
    mock_search_places.assert_called_once_with('몽탄')


@pytest.mark.django_db
def test_검색어가_비어있으면_400을_반환한다() -> None:
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    response = client.get(reverse('admin:places_place_kakao_search'), {'query': ''})

    assert response.status_code == 400


@pytest.mark.django_db
@patch('apps.places.admin.search_places')
def test_카카오_API_오류시_502를_반환한다(mock_search_places: MagicMock) -> None:
    mock_search_places.side_effect = KakaoApiError('카카오 로컬 API 호출 실패')
    staff = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)

    response = client.get(reverse('admin:places_place_kakao_search'), {'query': '몽탄'})

    assert response.status_code == 502
    assert response.json()['success'] is False
