from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.clubs.models import RecruitmentDetection, TrackedClub
from apps.clubs.services.llm_recruitment_detector import RecruitmentResult

_WEBHOOK = 'https://discord.com/api/webhooks/1/a'


def _make_club(**kwargs: object) -> TrackedClub:
    defaults = {
        'name': 'SOPT', 'homepage_url': 'https://www.sopt.org/', 'discord_webhook_url': _WEBHOOK,
    }
    defaults.update(kwargs)
    return TrackedClub.objects.create(**defaults)


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.ClubDiscordService.send_recruitment_alert')
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.extract_page_links')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_새로_모집이_열리면_알림을_보내고_상태를_올린다(
    mock_fetch: MagicMock, mock_links: MagicMock, mock_detect: MagicMock, mock_send: MagicMock,
) -> None:
    club = _make_club(is_recruiting_now=False)
    mock_fetch.return_value = '본문'
    mock_links.return_value = []
    mock_detect.return_value = RecruitmentResult(True, None, None, 'https://www.sopt.org/apply', '근거')
    mock_send.return_value = True

    call_command('check_club_recruitment')

    club.refresh_from_db()
    assert club.is_recruiting_now is True
    assert club.consecutive_failure_count == 0
    assert RecruitmentDetection.objects.filter(tracked_club=club, notify_succeeded=True).count() == 1


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.ClubDiscordService.send_recruitment_alert')
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.extract_page_links')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_이미_모집중_상태면_중복_알림을_보내지_않는다(
    mock_fetch: MagicMock, mock_links: MagicMock, mock_detect: MagicMock, mock_send: MagicMock,
) -> None:
    club = _make_club(is_recruiting_now=True)
    mock_fetch.return_value = '본문'
    mock_links.return_value = []
    mock_detect.return_value = RecruitmentResult(True, None, None, '', '근거')

    call_command('check_club_recruitment')

    mock_send.assert_not_called()
    assert RecruitmentDetection.objects.filter(tracked_club=club).count() == 0


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.extract_page_links')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_모집이_종료되면_상태를_내린다(
    mock_fetch: MagicMock, mock_links: MagicMock, mock_detect: MagicMock,
) -> None:
    club = _make_club(is_recruiting_now=True)
    mock_fetch.return_value = '본문'
    mock_links.return_value = []
    mock_detect.return_value = RecruitmentResult(False, None, None, '', '')

    call_command('check_club_recruitment')

    club.refresh_from_db()
    assert club.is_recruiting_now is False


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.ClubDiscordService.send_recruitment_alert')
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.extract_page_links')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_알림_발송_실패시_상태를_올리지_않아_다음_주기에_재시도한다(
    mock_fetch: MagicMock, mock_links: MagicMock, mock_detect: MagicMock, mock_send: MagicMock,
) -> None:
    club = _make_club(is_recruiting_now=False)
    mock_fetch.return_value = '본문'
    mock_links.return_value = []
    mock_detect.return_value = RecruitmentResult(True, None, None, '', '근거')
    mock_send.return_value = False

    call_command('check_club_recruitment')

    club.refresh_from_db()
    assert club.is_recruiting_now is False
    assert RecruitmentDetection.objects.filter(tracked_club=club, notify_succeeded=False).count() == 1


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.ClubDiscordService.send_failure_alert')
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_5회_연속_실패시_실패_경고를_1회만_보낸다(
    mock_fetch: MagicMock, mock_detect: MagicMock, mock_failure_alert: MagicMock,
) -> None:
    club = _make_club(consecutive_failure_count=4)
    mock_fetch.return_value = None
    mock_failure_alert.return_value = True

    call_command('check_club_recruitment')
    club.refresh_from_db()
    assert club.consecutive_failure_count == 5
    assert club.failure_alert_sent is True
    mock_failure_alert.assert_called_once()

    call_command('check_club_recruitment')
    club.refresh_from_db()
    assert club.consecutive_failure_count == 6
    mock_failure_alert.assert_called_once()  # 두 번째 호출에서는 추가로 불리지 않음
    mock_detect.assert_not_called()


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_비활성_동아리는_건너뛴다(mock_fetch: MagicMock, mock_detect: MagicMock) -> None:
    _make_club(is_active=False)

    call_command('check_club_recruitment')

    mock_fetch.assert_not_called()
    mock_detect.assert_not_called()


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.extract_page_links')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_한_동아리에서_예상치_못한_예외가_발생해도_다음_동아리를_계속_처리한다(
    mock_fetch: MagicMock, mock_links: MagicMock, mock_detect: MagicMock,
) -> None:
    _make_club(name='실패동아리', homepage_url='https://fail.example.com/')
    _make_club(name='정상동아리', homepage_url='https://ok.example.com/')
    mock_fetch.side_effect = [RuntimeError('boom'), '본문']
    mock_links.return_value = []
    mock_detect.return_value = RecruitmentResult(False, None, None, '', '')

    call_command('check_club_recruitment')

    # 첫 번째 동아리에서 예외가 나도 루프가 중단되지 않고 두 번째 동아리까지 처리됐는지 확인
    mock_detect.assert_called_once_with('정상동아리', '본문', [])


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_예상치_못한_예외도_실패_카운터에_반영된다(mock_fetch: MagicMock, mock_detect: MagicMock) -> None:
    # 예외 경로가 로그만 남기고 _handle_failure를 거치지 않으면, 이 경로로 반복 실패해도
    # consecutive_failure_count가 절대 오르지 않아 5회 연속 실패 경고가 영원히 발동하지 않는다.
    club = _make_club()
    mock_fetch.side_effect = RuntimeError('boom')

    call_command('check_club_recruitment')

    club.refresh_from_db()
    assert club.consecutive_failure_count == 1
    mock_detect.assert_not_called()


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.Command._handle_failure')
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.extract_page_links')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_실패_카운터_반영_자체가_실패해도_다음_동아리를_계속_처리한다(
    mock_fetch: MagicMock, mock_links: MagicMock, mock_detect: MagicMock, mock_handle_failure: MagicMock,
) -> None:
    # 원 예외가 DB 쓰기 오류였다면 _handle_failure의 club.save()도 같은 이유로 실패할 수 있다 —
    # 그 2차 예외가 밖으로 새어나가 남은 동아리 확인 전체를 중단시키지 않는지 검증한다.
    _make_club(name='실패동아리', homepage_url='https://fail.example.com/')
    _make_club(name='정상동아리', homepage_url='https://ok.example.com/')
    mock_fetch.side_effect = [RuntimeError('boom'), '본문']
    mock_links.return_value = []
    mock_detect.return_value = RecruitmentResult(False, None, None, '', '')
    mock_handle_failure.side_effect = RuntimeError('save 실패')

    call_command('check_club_recruitment')

    mock_detect.assert_called_once_with('정상동아리', '본문', [])


@pytest.mark.django_db
@patch('apps.clubs.management.commands.check_club_recruitment.ClubDiscordService.send_recruitment_alert')
@patch('apps.clubs.management.commands.check_club_recruitment.detect_recruitment')
@patch('apps.clubs.management.commands.check_club_recruitment.fetch_page_text')
def test_웹훅_미설정_동아리는_확인_자체를_건너뛴다(
    mock_fetch: MagicMock, mock_detect: MagicMock, mock_send: MagicMock,
) -> None:
    _make_club(discord_webhook_url='')

    call_command('check_club_recruitment')

    # 웹훅이 없으면 fetch·판별까지 가지 않고 handle()에서 곧바로 건너뛴다 — 웹훅을 채우기
    # 전까지 매 주기 LLM을 호출하는 낭비를 막기 위함(Task 6 설계 참고).
    mock_fetch.assert_not_called()
    mock_detect.assert_not_called()
    mock_send.assert_not_called()
