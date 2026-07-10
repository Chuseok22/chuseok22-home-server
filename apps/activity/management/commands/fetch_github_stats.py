import logging

from django.core.management.base import BaseCommand

from apps.activity.models import GithubContributionDay, GithubProfileStats
from apps.activity.services.github_stats import GithubStatsService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'GitHub GraphQL API로 컨트리뷰션 캘린더와 총 star 수를 수집해 DB에 캐싱한다'

    def handle(self, *args, **options) -> None:
        stats = GithubStatsService().fetch()
        if not stats.contribution_days:
            self.stdout.write('수집된 컨트리뷰션 데이터가 없습니다.')
            return

        for day in stats.contribution_days:
            GithubContributionDay.objects.update_or_create(
                date=day.date,
                defaults={'contribution_count': day.contribution_count},
            )

        GithubProfileStats.objects.update_or_create(
            pk=1,
            defaults={'total_stars': stats.total_stars},
        )

        self.stdout.write(
            f'컨트리뷰션 {len(stats.contribution_days)}일치 저장, 총 star {stats.total_stars}개 갱신',
        )
