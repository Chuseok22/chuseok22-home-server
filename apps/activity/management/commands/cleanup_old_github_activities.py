from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.activity.models import GithubActivity
from apps.core.services.retention import delete_expired_records

_RETENTION_DAYS = 7


class Command(BaseCommand):
    help = 'occurred_at 기준 7일이 지난 GithubActivity 레코드를 삭제한다'

    def handle(self, *args: object, **options: object) -> None:
        cutoff = timezone.now() - timedelta(days=_RETENTION_DAYS)
        deleted = delete_expired_records(
            GithubActivity.objects.filter(occurred_at__lt=cutoff),
            label='GitHub 활동',
        )
        self.stdout.write(f'GithubActivity {deleted}건 삭제 완료 (기준: {_RETENTION_DAYS}일)')
