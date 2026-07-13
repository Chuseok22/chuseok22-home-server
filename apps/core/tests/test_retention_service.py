from datetime import timedelta

import pytest
from django.utils import timezone

from apps.activity.models import GithubActivity
from apps.core.services.retention import delete_expired_records


@pytest.mark.django_db
def test_delete_expired_records는_filtered_queryset을_삭제하고_건수를_반환한다() -> None:
    old_time = timezone.now() - timedelta(days=10)
    recent_time = timezone.now() - timedelta(days=1)
    GithubActivity.objects.create(
        event_id='old-1', event_type='PushEvent', repo_name='chuseok22/test',
        title='title', meta='meta', occurred_at=old_time,
    )
    GithubActivity.objects.create(
        event_id='recent-1', event_type='PushEvent', repo_name='chuseok22/test',
        title='title', meta='meta', occurred_at=recent_time,
    )
    cutoff = timezone.now() - timedelta(days=7)

    deleted = delete_expired_records(
        GithubActivity.objects.filter(occurred_at__lt=cutoff),
        label='GitHub 활동',
    )

    assert deleted == 1
    assert GithubActivity.objects.count() == 1
    assert GithubActivity.objects.get().event_id == 'recent-1'


@pytest.mark.django_db
def test_delete_expired_records는_삭제_대상이_없으면_0을_반환한다() -> None:
    deleted = delete_expired_records(GithubActivity.objects.none(), label='GitHub 활동')

    assert deleted == 0
