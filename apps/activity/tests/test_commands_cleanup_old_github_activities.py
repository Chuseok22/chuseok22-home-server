from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.activity.models import GithubActivity


def _create_activity(event_id: str, days_ago: int) -> GithubActivity:
    return GithubActivity.objects.create(
        event_id=event_id,
        event_type='PushEvent',
        repo_name='chuseok22/test',
        title='title',
        meta='meta',
        occurred_at=timezone.now() - timedelta(days=days_ago),
    )


@pytest.mark.django_db
def test_cleanup_old_github_activities는_7일_초과_레코드를_삭제한다() -> None:
    _create_activity('old-1', days_ago=10)
    _create_activity('recent-1', days_ago=1)

    call_command('cleanup_old_github_activities')

    assert GithubActivity.objects.count() == 1
    assert GithubActivity.objects.filter(event_id='recent-1').exists()


@pytest.mark.django_db
def test_cleanup_old_github_activities는_7일_이내_레코드는_유지한다() -> None:
    _create_activity('recent-1', days_ago=6)
    _create_activity('recent-2', days_ago=1)

    call_command('cleanup_old_github_activities')

    assert GithubActivity.objects.count() == 2


@pytest.mark.django_db
def test_cleanup_old_github_activities는_경계값_7일_전_레코드를_삭제한다() -> None:
    _create_activity('boundary-1', days_ago=7)

    call_command('cleanup_old_github_activities')

    assert GithubActivity.objects.count() == 0
