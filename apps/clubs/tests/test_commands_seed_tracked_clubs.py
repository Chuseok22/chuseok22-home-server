import pytest
from django.core.management import call_command

from apps.clubs.models import TrackedClub


@pytest.mark.django_db
def test_초기_3개_동아리를_생성한다() -> None:
    call_command('seed_tracked_clubs')

    names = set(TrackedClub.objects.values_list('name', flat=True))
    assert names == {'YAPP', 'NEXTERS', 'Mash-Up'}
    yapp = TrackedClub.objects.get(name='YAPP')
    assert yapp.homepage_url == 'https://www.yapp.co.kr/recruit'
    assert yapp.discord_webhook_url == ''


@pytest.mark.django_db
def test_이미_존재하는_동아리는_건너뛰고_기존_값을_유지한다() -> None:
    call_command('seed_tracked_clubs')
    TrackedClub.objects.filter(name='YAPP').update(homepage_url='https://www.yapp.co.kr/recruit/25')

    call_command('seed_tracked_clubs')

    assert TrackedClub.objects.filter(name='YAPP').count() == 1
    assert TrackedClub.objects.get(name='YAPP').homepage_url == 'https://www.yapp.co.kr/recruit/25'
