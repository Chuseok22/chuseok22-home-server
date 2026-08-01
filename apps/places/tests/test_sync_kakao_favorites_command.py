from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.places.models import Place, PlaceSyncFolder
from apps.places.services.kakao_favorite_sync import ChangedPlace, KakaoFavoriteSyncError, SyncResult


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_활성_폴더만_순회한다(mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock) -> None:
    mock_sync_folder.return_value = SyncResult(created_count=1, skipped_count=0, changed_places=[])
    active = PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', is_active=True)
    PlaceSyncFolder.objects.create(category=Place.Category.CAFE, kakao_folder_id='2', is_active=False)

    call_command('sync_kakao_favorites', stdout=StringIO())

    mock_sync_folder.assert_called_once_with(active)


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_한_폴더_실패가_다른_폴더_처리를_막지_않는다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    PlaceSyncFolder.objects.create(category=Place.Category.CAFE, kakao_folder_id='2', title='카페')
    mock_sync_folder.side_effect = [
        KakaoFavoriteSyncError('실패'),
        SyncResult(created_count=2, skipped_count=0, changed_places=[]),
    ]

    out = StringIO()
    err = StringIO()
    call_command('sync_kakao_favorites', stdout=out, stderr=err)

    assert mock_sync_folder.call_count == 2
    assert '실패' in err.getvalue()
    assert '카페' in out.getvalue()
    assert '신규 2건' in out.getvalue()


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_예상치_못한_예외도_한_폴더만_실패시키고_계속_진행한다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    # KakaoFavoriteSyncError가 아닌 예외(예: DB 오류)도 커맨드 전체를 중단시키면 안 된다 —
    # 스케줄러가 예외를 삼키므로, 중단되면 나머지 폴더 동기화와 이미 모은 알림 발송도 사라진다.
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    PlaceSyncFolder.objects.create(category=Place.Category.CAFE, kakao_folder_id='2', title='카페')
    mock_sync_folder.side_effect = [
        RuntimeError('예상 못한 DB 오류'),
        SyncResult(created_count=2, skipped_count=0, changed_places=[]),
    ]

    out = StringIO()
    err = StringIO()
    call_command('sync_kakao_favorites', stdout=out, stderr=err)

    assert mock_sync_folder.call_count == 2
    assert '예기치 못한 오류' in err.getvalue()
    assert '신규 2건' in out.getvalue()


@pytest.mark.django_db
def test_활성_폴더가_없으면_안내_메시지를_출력한다() -> None:
    out = StringIO()
    call_command('sync_kakao_favorites', stdout=out)
    assert '활성화된 동기화 폴더가 없습니다' in out.getvalue()


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_변경_감지된_장소가_있으면_텔레그램_알림을_보낸다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    mock_sync_folder.return_value = SyncResult(
        created_count=0, skipped_count=1,
        changed_places=[ChangedPlace(name='이이요', kakao_place_url='https://place.map.kakao.com/1')],
    )
    mock_telegram_instance = mock_telegram_cls.return_value

    call_command('sync_kakao_favorites', stdout=StringIO())

    mock_telegram_instance.send_admin_alert.assert_called_once()
    message = mock_telegram_instance.send_admin_alert.call_args.args[0]
    assert '이이요' in message


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_변경_감지된_장소가_없으면_텔레그램_알림을_보내지_않는다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    mock_sync_folder.return_value = SyncResult(created_count=1, skipped_count=0, changed_places=[])

    call_command('sync_kakao_favorites', stdout=StringIO())

    mock_telegram_cls.return_value.send_admin_alert.assert_not_called()


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_폴더_동기화가_실패하면_텔레그램으로_실패_알림을_보낸다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    # 스케줄러가 예외를 삼키므로, 실패 사실이 알림으로 전달되지 않으면 관리자가 인지할 수 없다.
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    PlaceSyncFolder.objects.create(category=Place.Category.CAFE, kakao_folder_id='2', title='카페')
    mock_sync_folder.side_effect = [
        KakaoFavoriteSyncError('응답 형식 이상'),
        SyncResult(created_count=1, skipped_count=0, changed_places=[]),
    ]
    mock_telegram_instance = mock_telegram_cls.return_value

    call_command('sync_kakao_favorites', stdout=StringIO(), stderr=StringIO())

    mock_telegram_instance.send_admin_alert.assert_called_once()
    message = mock_telegram_instance.send_admin_alert.call_args.args[0]
    assert '동기화 실패' in message
    # PlaceSyncFolder는 category 순으로 조회되므로 카페 폴더가 먼저 처리되어 실패한다.
    assert '카페' in message
    assert '맛집' not in message


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_실패와_변경_감지가_함께_있으면_두_알림을_모두_보낸다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    PlaceSyncFolder.objects.create(category=Place.Category.CAFE, kakao_folder_id='2', title='카페')
    mock_sync_folder.side_effect = [
        KakaoFavoriteSyncError('응답 형식 이상'),
        SyncResult(
            created_count=0, skipped_count=1,
            changed_places=[ChangedPlace(name='이이요', kakao_place_url='https://place.map.kakao.com/1')],
        ),
    ]
    mock_telegram_instance = mock_telegram_cls.return_value

    call_command('sync_kakao_favorites', stdout=StringIO(), stderr=StringIO())

    messages = [call.args[0] for call in mock_telegram_instance.send_admin_alert.call_args_list]
    assert len(messages) == 2
    assert '동기화 실패' in messages[0]
    assert '이이요' in messages[1]


@pytest.mark.django_db
@patch('apps.places.management.commands.sync_kakao_favorites.TelegramService')
@patch('apps.places.management.commands.sync_kakao_favorites.sync_folder')
def test_변경_감지_장소가_많으면_메시지를_여러_건으로_나눠_보낸다(
    mock_sync_folder: MagicMock, mock_telegram_cls: MagicMock,
) -> None:
    PlaceSyncFolder.objects.create(category=Place.Category.RESTAURANT, kakao_folder_id='1', title='맛집')
    many_changed = [
        ChangedPlace(name=f'장소{i}', kakao_place_url=f'https://place.map.kakao.com/{i}')
        for i in range(200)
    ]
    mock_sync_folder.return_value = SyncResult(created_count=0, skipped_count=200, changed_places=many_changed)
    mock_telegram_instance = mock_telegram_cls.return_value

    call_command('sync_kakao_favorites', stdout=StringIO())

    assert mock_telegram_instance.send_admin_alert.call_count > 1
    for call in mock_telegram_instance.send_admin_alert.call_args_list:
        assert len(call.args[0]) <= 4096
