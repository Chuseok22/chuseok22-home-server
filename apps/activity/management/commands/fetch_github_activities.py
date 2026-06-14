import logging

from django.core.management.base import BaseCommand

from apps.activity.models import GithubActivity
from apps.activity.services.github import GithubService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'GitHub Public Events API로 활동 이력을 수집해 DB에 캐싱한다'

    def handle(self, *args, **options) -> None:
        items = GithubService().fetch_events()
        if not items:
            self.stdout.write('수집된 활동이 없습니다.')
            return

        created = 0
        for item in items:
            _, is_created = GithubActivity.objects.update_or_create(
                event_id=item.event_id,
                defaults={
                    'event_type': item.event_type,
                    'repo_name': item.repo_name,
                    'title': item.title,
                    'meta': item.meta,
                    'occurred_at': item.occurred_at,
                },
            )
            if is_created:
                created += 1

        self.stdout.write(f'{len(items)}건 수집 → {created}건 신규 저장 (나머지는 갱신)')
