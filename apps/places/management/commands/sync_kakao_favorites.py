import logging

from django.core.management.base import BaseCommand

from apps.notifications.services.telegram import TelegramService
from apps.places.models import PlaceSyncFolder
from apps.places.services.kakao_favorite_sync import ChangedPlace, KakaoFavoriteSyncError, sync_folder

logger = logging.getLogger(__name__)

# 텔레그램 sendMessage의 4096자 제한을 넘지 않도록, 한 메시지에 담을 장소 수를 제한한다.
_MAX_PLACES_PER_MESSAGE = 30


class Command(BaseCommand):
    help = '활성화된 PlaceSyncFolder를 순회하며 카카오맵 즐겨찾기를 Place로 동기화한다'

    def handle(self, *args: object, **options: object) -> None:
        folders = PlaceSyncFolder.objects.filter(is_active=True)
        if not folders.exists():
            self.stdout.write('활성화된 동기화 폴더가 없습니다.')
            return

        all_changed: list[ChangedPlace] = []
        failed_labels: list[str] = []
        for folder in folders:
            label = folder.title or folder.kakao_folder_id
            self.stdout.write(f'[{label}] 동기화 시작')
            try:
                result = sync_folder(folder)
            except KakaoFavoriteSyncError as e:
                logger.error('폴더 동기화 실패 (folder_id=%s): %s', folder.kakao_folder_id, e)
                self.stderr.write(f'[{label}] 동기화 실패: {e}')
                failed_labels.append(label)
                continue
            self.stdout.write(f'[{label}] 신규 {result.created_count}건, 스킵 {result.skipped_count}건')
            all_changed.extend(result.changed_places)

        if all_changed or failed_labels:
            self._notify(all_changed, failed_labels)

    def _notify(self, changed_places: list[ChangedPlace], failed_labels: list[str]) -> None:
        telegram = TelegramService()

        # 스케줄러는 예외를 로깅만 하고 삼키므로, 폴더 동기화 실패도 알림으로 알려야 관리자가 인지할 수 있다.
        if failed_labels:
            failure_lines = '\n'.join(f'- {label}' for label in failed_labels)
            failure_message = (
                f'⚠️ 카카오맵 즐겨찾기 동기화 실패 ({len(failed_labels)}개 폴더)\n{failure_lines}'
            )
            if not telegram.send_admin_alert(failure_message):
                self.stderr.write('동기화 실패 알림 발송 실패')

        if not changed_places:
            return

        total = len(changed_places)
        chunks = [
            changed_places[i:i + _MAX_PLACES_PER_MESSAGE]
            for i in range(0, total, _MAX_PLACES_PER_MESSAGE)
        ]
        for index, chunk in enumerate(chunks, start=1):
            lines = [f'- {place.name} ({place.kakao_place_url})' for place in chunk]
            page_label = f' ({index}/{len(chunks)})' if len(chunks) > 1 else ''
            message = (
                f'📍 카카오맵 즐겨찾기 변경 감지 ({total}건){page_label}\n'
                '아래 장소의 정보가 카카오맵에서 바뀌었을 수 있습니다. 폐업/이전 여부를 확인해주세요.\n'
                + '\n'.join(lines)
            )
            if not telegram.send_admin_alert(message):
                self.stderr.write(f'변경 감지 알림 발송 실패 ({index}/{len(chunks)})')
