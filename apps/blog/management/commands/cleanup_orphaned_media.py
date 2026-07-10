from django.core.management.base import BaseCommand

from apps.blog.services.media_storage import delete_media_files, find_orphaned_media

_GRACE_PERIOD_SECONDS = 24 * 60 * 60


class Command(BaseCommand):
    help = '어떤 포스트에도 참조되지 않는 blog/uploads 하위 파일을 정리한다'

    def handle(self, *args: object, **options: object) -> None:
        orphaned_paths = find_orphaned_media(grace_seconds=_GRACE_PERIOD_SECONDS)
        delete_media_files(orphaned_paths)
        self.stdout.write(f'고아 파일 {len(orphaned_paths)}개 삭제 완료.')
