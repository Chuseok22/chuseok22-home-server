from unittest.mock import MagicMock, patch

import pytest
import requests
from django.test import TestCase

from apps.places.models import Place, PlaceSyncFolder
from apps.places.services.kakao_favorite_sync import KakaoFavoriteSyncError, resolve_folder_id, sync_folder

_SAMPLE_ITEM = {
    'seq': 522623802, 'type': 'PLACE', 'display1': '이이요', 'display2': '서울 광진구 능동로32길 6 (능동)',
    'memo': '일식', 'key': '861945610', 'lon': 127.07890418, 'lat': 37.55518592,
    'item_updated_at': '2023-05-03 12:41:35',
}


@pytest.mark.django_db
class TestSyncFolder(TestCase):
    def setUp(self) -> None:
        self.folder = PlaceSyncFolder.objects.create(
            category=Place.Category.RESTAURANT, kakao_folder_id='10340963', title='맛집',
        )

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_신규_장소는_Place로_생성된다(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'favorites': [_SAMPLE_ITEM], 'next_id': None}
        mock_get.return_value = mock_response

        result = sync_folder(self.folder)

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.changed_places, [])
        place = Place.objects.get(kakao_place_id='861945610')
        self.assertEqual(place.name, '이이요')
        self.assertEqual(place.address, '서울 광진구 능동로32길 6 (능동)')
        self.assertEqual(place.note, '일식')
        self.assertEqual(place.category, Place.Category.RESTAURANT)
        self.assertEqual(place.kakao_place_url, 'https://place.map.kakao.com/861945610')
        self.assertEqual(place.kakao_item_updated_at, '2023-05-03 12:41:35')
        self.assertEqual(float(place.latitude), 37.5551859)
        self.assertEqual(float(place.longitude), 127.0789042)
        mock_get.assert_called_once_with(
            'https://map.kakao.com/favorite/list',
            headers={'Referer': 'https://map.kakao.com/'},
            params={'folderid': '10340963'},
            timeout=(5, 10),
        )

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_처음_동기화되는_기존_수동등록_장소는_알림_없이_기준값만_채운다(self, mock_get: MagicMock) -> None:
        # kakao_item_updated_at=''(수동 등록 등으로 아직 추적 시작 전)인 기존 장소는
        # 첫 동기화에서 "변경 감지"로 오탐되면 안 된다.
        Place.objects.create(
            name='이이요', latitude=37.0, longitude=127.0, kakao_place_id='861945610', kakao_item_updated_at='',
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'favorites': [_SAMPLE_ITEM], 'next_id': None}
        mock_get.return_value = mock_response

        result = sync_folder(self.folder)

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.changed_places, [])
        place = Place.objects.get(kakao_place_id='861945610')
        self.assertEqual(place.kakao_item_updated_at, '2023-05-03 12:41:35')

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_변경이_없는_기존_장소는_건너뛰고_변경_목록에도_없다(self, mock_get: MagicMock) -> None:
        Place.objects.create(
            name='이이요(기존)', latitude=37.0, longitude=127.0, kakao_place_id='861945610',
            kakao_item_updated_at='2023-05-03 12:41:35',
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'favorites': [_SAMPLE_ITEM], 'next_id': None}
        mock_get.return_value = mock_response

        result = sync_folder(self.folder)

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.changed_places, [])

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_item_updated_at이_바뀐_기존_장소는_변경_목록에만_담기고_이름은_바뀌지_않는다(
        self, mock_get: MagicMock,
    ) -> None:
        Place.objects.create(
            name='이이요(원래이름)', latitude=37.0, longitude=127.0, kakao_place_id='861945610',
            kakao_item_updated_at='2023-05-03 12:41:35',
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'favorites': [{**_SAMPLE_ITEM, 'display1': '이이요(바뀐이름)', 'item_updated_at': '2026-01-01 00:00:00'}],
            'next_id': None,
        }
        mock_get.return_value = mock_response

        result = sync_folder(self.folder)

        self.assertEqual(len(result.changed_places), 1)
        self.assertEqual(result.changed_places[0].name, '이이요(원래이름)')
        place = Place.objects.get(kakao_place_id='861945610')
        self.assertEqual(place.name, '이이요(원래이름)')
        self.assertEqual(place.kakao_item_updated_at, '2026-01-01 00:00:00')

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_페이지네이션으로_여러_페이지를_모두_처리한다(self, mock_get: MagicMock) -> None:
        page1 = MagicMock(status_code=200)
        page1.json.return_value = {
            'favorites': [
                {**_SAMPLE_ITEM, 'key': '1'},
                {**_SAMPLE_ITEM, 'key': '2'},
            ],
            'next_id': 2,
        }
        page2 = MagicMock(status_code=200)
        page2.json.return_value = {'favorites': [{**_SAMPLE_ITEM, 'key': '3'}], 'next_id': None}
        mock_get.side_effect = [page1, page2]

        result = sync_folder(self.folder)

        self.assertEqual(result.created_count, 3)
        self.assertEqual(mock_get.call_count, 2)
        second_call_params = mock_get.call_args_list[1].kwargs['params']
        self.assertEqual(second_call_params, {'folderid': '10340963', 'next_id': 2})

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_next_id가_반복되면_무한루프_없이_종료한다(self, mock_get: MagicMock) -> None:
        page = MagicMock(status_code=200)
        page.json.return_value = {'favorites': [{**_SAMPLE_ITEM, 'key': '1'}], 'next_id': 999}
        mock_get.return_value = page

        sync_folder(self.folder)

        # next_id=999가 반복되므로 첫 호출 + 같은 next_id로 한 번 더 확인한 뒤 중단되어야 한다
        self.assertEqual(mock_get.call_count, 2)

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_네트워크_오류시_KakaoFavoriteSyncError_발생(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError('connection refused')

        with self.assertRaises(KakaoFavoriteSyncError):
            sync_folder(self.folder)

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_favorites_키가_없는_응답은_KakaoFavoriteSyncError_발생(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'meta': {}}
        mock_get.return_value = mock_response

        with self.assertRaises(KakaoFavoriteSyncError):
            sync_folder(self.folder)

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_항목에_필수_키가_없으면_KakaoFavoriteSyncError_발생(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'favorites': [{'type': 'PLACE'}], 'next_id': None}
        mock_get.return_value = mock_response

        with self.assertRaises(KakaoFavoriteSyncError):
            sync_folder(self.folder)

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_동기화_후_last_synced_at이_갱신된다(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'favorites': [_SAMPLE_ITEM], 'next_id': None}
        mock_get.return_value = mock_response

        self.assertIsNone(self.folder.last_synced_at)
        sync_folder(self.folder)

        self.folder.refresh_from_db()
        self.assertIsNotNone(self.folder.last_synced_at)


class TestResolveFolderId(TestCase):
    def test_이미_숫자_ID면_그대로_반환한다(self) -> None:
        self.assertEqual(resolve_folder_id('10340963'), '10340963')

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_공유_링크는_리다이렉트를_따라가_folderid를_추출한다(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://map.kakao.com/?map_type=TYPE_MAP&folderid=10340963&target=other&page=bookmark'
        mock_get.return_value = mock_response

        result = resolve_folder_id('https://kko.to/KVWPW2bHLZ')

        self.assertEqual(result, '10340963')
        mock_get.assert_called_once_with(
            'https://kko.to/KVWPW2bHLZ',
            headers={'Referer': 'https://map.kakao.com/'},
            allow_redirects=True,
            timeout=(5, 10),
        )

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_folderid_없는_링크는_KakaoFavoriteSyncError_발생(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://map.kakao.com/'
        mock_get.return_value = mock_response

        with self.assertRaises(KakaoFavoriteSyncError):
            resolve_folder_id('https://kko.to/invalid')

    @patch('apps.places.services.kakao_favorite_sync.requests.get')
    def test_링크_해석_네트워크_오류시_KakaoFavoriteSyncError_발생(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError('connection refused')

        with self.assertRaises(KakaoFavoriteSyncError):
            resolve_folder_id('https://kko.to/KVWPW2bHLZ')
