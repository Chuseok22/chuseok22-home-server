from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from apps.places.services.kakao import KakaoApiError, search_places

_SAMPLE_DOCUMENT = {
    'place_name': '몽탄',
    'address_name': '서울 성동구 성수동2가 289-13',
    'road_address_name': '서울 성동구 서울숲2길 32-14',
    'category_name': '음식점 > 한식 > 육류,고기 > 갈비',
    'phone': '02-462-2262',
    'x': '127.0442254',
    'y': '37.5445037',
    'place_url': 'http://place.map.kakao.com/1273083863',
}


@override_settings(KAKAO_REST_API_KEY='test-rest-key')
class TestSearchPlaces(TestCase):
    @patch('apps.places.services.kakao.requests.get')
    def test_정상_응답시_KakaoPlaceResult_리스트_반환(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'documents': [_SAMPLE_DOCUMENT], 'meta': {'total_count': 1}}
        mock_get.return_value = mock_response

        results = search_places('몽탄')

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.name, '몽탄')
        self.assertEqual(result.address, '서울 성동구 성수동2가 289-13')
        self.assertEqual(result.road_address, '서울 성동구 서울숲2길 32-14')
        self.assertEqual(result.latitude, 37.5445037)
        self.assertEqual(result.longitude, 127.0442254)
        self.assertEqual(result.category, '음식점 > 한식 > 육류,고기 > 갈비')
        self.assertEqual(result.place_url, 'http://place.map.kakao.com/1273083863')
        mock_get.assert_called_once_with(
            'https://dapi.kakao.com/v2/local/search/keyword.json',
            headers={'Authorization': 'KakaoAK test-rest-key'},
            params={'query': '몽탄'},
            timeout=(5, 10),
        )

    @patch('apps.places.services.kakao.requests.get')
    def test_검색결과가_없으면_빈_리스트_반환(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'documents': [], 'meta': {'total_count': 0}}
        mock_get.return_value = mock_response

        self.assertEqual(search_places('존재하지않는맛집'), [])

    @patch('apps.places.services.kakao.requests.get')
    def test_좌표는_소수점_7자리로_반올림된다(self, mock_get: MagicMock) -> None:
        # 카카오 API가 실제로 소수점 7자리를 초과하는 좌표를 반환하는 경우가 흔한데,
        # Place.latitude/longitude가 DecimalField(decimal_places=7)이라 그대로
        # 저장하면 Admin 폼 검증에서 실패한다. 서비스 레벨에서 미리 반올림해 이를 막는다.
        document = {**_SAMPLE_DOCUMENT, 'x': '127.10866424103800', 'y': '37.54450371234567'}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'documents': [document], 'meta': {'total_count': 1}}
        mock_get.return_value = mock_response

        result = search_places('몽탄')[0]

        self.assertEqual(result.latitude, 37.5445037)
        self.assertEqual(result.longitude, 127.1086642)


@override_settings(KAKAO_REST_API_KEY='test-rest-key')
class TestSearchPlacesErrors(TestCase):
    @patch('apps.places.services.kakao.requests.get')
    def test_비2xx_응답시_KakaoApiError_발생(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            '401 Client Error', response=mock_response
        )
        mock_get.return_value = mock_response

        with self.assertRaises(KakaoApiError):
            search_places('몽탄')

    @patch('apps.places.services.kakao.requests.get')
    def test_네트워크_연결_오류시_KakaoApiError_발생(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError('connection refused')

        with self.assertRaises(KakaoApiError):
            search_places('몽탄')

    @patch('apps.places.services.kakao.requests.get')
    def test_응답에_documents_키_없을때_KakaoApiError_발생(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'meta': {'total_count': 0}}
        mock_get.return_value = mock_response

        with self.assertRaises(KakaoApiError):
            search_places('몽탄')
