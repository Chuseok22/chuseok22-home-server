from datetime import date
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.activity.models import GithubContributionDay, GithubProfileStats
from apps.activity.services.github_stats import ContributionDay, GithubStats


@pytest.mark.django_db
def test_fetch_github_stats는_컨트리뷰션과_총_star를_저장한다() -> None:
    stats = GithubStats(
        contribution_days=(
            ContributionDay(date=date(2026, 1, 1), contribution_count=5),
            ContributionDay(date=date(2026, 1, 2), contribution_count=0),
        ),
        total_stars=8,
    )

    with patch(
        'apps.activity.services.github_stats.GithubStatsService.fetch',
        return_value=stats,
    ):
        call_command('fetch_github_stats')

    assert GithubContributionDay.objects.count() == 2
    assert GithubContributionDay.objects.get(date=date(2026, 1, 1)).contribution_count == 5
    assert GithubProfileStats.objects.get(pk=1).total_stars == 8


@pytest.mark.django_db
def test_fetch_github_stats는_기존_레코드를_갱신한다() -> None:
    GithubContributionDay.objects.create(date=date(2026, 1, 1), contribution_count=1)
    GithubProfileStats.objects.create(pk=1, total_stars=1)

    stats = GithubStats(
        contribution_days=(ContributionDay(date=date(2026, 1, 1), contribution_count=9),),
        total_stars=10,
    )

    with patch(
        'apps.activity.services.github_stats.GithubStatsService.fetch',
        return_value=stats,
    ):
        call_command('fetch_github_stats')

    assert GithubContributionDay.objects.count() == 1
    assert GithubContributionDay.objects.get(date=date(2026, 1, 1)).contribution_count == 9
    assert GithubProfileStats.objects.get(pk=1).total_stars == 10


@pytest.mark.django_db
def test_fetch_github_stats는_데이터가_없으면_아무것도_저장하지_않는다() -> None:
    empty_stats = GithubStats(contribution_days=(), total_stars=0)

    with patch(
        'apps.activity.services.github_stats.GithubStatsService.fetch',
        return_value=empty_stats,
    ):
        call_command('fetch_github_stats')

    assert GithubContributionDay.objects.count() == 0
    assert GithubProfileStats.objects.count() == 0
