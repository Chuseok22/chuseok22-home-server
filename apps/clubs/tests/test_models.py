import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.clubs.models import RecruitmentDetection, TrackedClub, validate_discord_webhook_url


def test_validate_discord_webhook_url_정상_URL은_통과한다() -> None:
    validate_discord_webhook_url('https://discord.com/api/webhooks/123/abc')


@pytest.mark.parametrize('value', [
    'http://discord.com/api/webhooks/123/abc',  # https 아님
    'https://evil.com/api/webhooks/123/abc',    # 허용되지 않은 호스트
    'https://discord.com/not-webhooks/123/abc', # 경로 형식 불일치
])
def test_validate_discord_webhook_url_비정상_URL은_거부한다(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_discord_webhook_url(value)


@pytest.mark.django_db
def test_TrackedClub_기본값() -> None:
    club = TrackedClub.objects.create(name='SOPT', homepage_url='https://www.sopt.org/')
    assert club.is_active is True
    assert club.discord_webhook_url == ''
    assert club.is_recruiting_now is False
    assert club.last_checked_at is None
    assert club.consecutive_failure_count == 0
    assert club.failure_alert_sent is False
    assert str(club) == 'SOPT'


@pytest.mark.django_db
def test_TrackedClub_name은_유일해야_한다() -> None:
    TrackedClub.objects.create(name='SOPT', homepage_url='https://www.sopt.org/')
    with pytest.raises(IntegrityError):
        TrackedClub.objects.create(name='SOPT', homepage_url='https://www.sopt.org/apply')


@pytest.mark.django_db
def test_RecruitmentDetection_생성_및_FK_연결() -> None:
    club = TrackedClub.objects.create(name='YAPP', homepage_url='https://www.yapp.co.kr/')
    detection = RecruitmentDetection.objects.create(
        tracked_club=club,
        application_start='2026-09-01',
        application_end='2026-09-14',
        apply_url='https://www.yapp.co.kr/apply',
        evidence_quote='25기 지원 기간: 09.01 ~ 09.14',
    )
    assert detection.notify_succeeded is False
    assert detection.tracked_club == club
    assert club.detections.count() == 1
