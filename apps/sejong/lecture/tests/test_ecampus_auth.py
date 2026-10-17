from unittest.mock import MagicMock, patch

import logging

import pytest

from apps.sejong.lecture.models import SejongAccount
from apps.sejong.lecture.services.ecampus_auth import (
    EcampusMoodleAuthService,
    EcampusSession,
    _is_login_successful,
    _NetworkLoginError,
)


def _make_response(url: str, text: str) -> MagicMock:
    response = MagicMock()
    response.url = url
    response.text = text
    return response


def test_is_login_successful_true_when_redirected_away_from_login_with_logout_link() -> None:
    response = _make_response(
        url='https://ecampus.sejong.ac.kr/',
        text='<html><body><a href="logout.php">로그아웃</a></body></html>',
    )

    assert _is_login_successful(response) is True


def test_is_login_successful_false_when_still_on_login_page() -> None:
    response = _make_response(
        url='https://ecampus.sejong.ac.kr/login/index.php',
        text='<html><body><a href="logout.php">로그아웃</a></body></html>',
    )

    assert _is_login_successful(response) is False


def test_is_login_successful_false_when_redirected_but_no_logout_link() -> None:
    response = _make_response(
        url='https://ecampus.sejong.ac.kr/',
        text='<html><body>로그인에 실패했습니다.</body></html>',
    )

    assert _is_login_successful(response) is False


def test_create_session_returns_cached_session_without_relogin() -> None:
    service = EcampusMoodleAuthService()
    first_session = EcampusSession(session=MagicMock())

    with patch.object(EcampusMoodleAuthService, '_login', return_value=first_session) as mock_login:
        result1 = service.create_session()
        result2 = service.create_session()

    assert result1 is first_session
    assert result2 is first_session
    mock_login.assert_called_once()


def test_create_session_force_refresh_relogins_when_stale_matches_cache() -> None:
    service = EcampusMoodleAuthService()
    stale_session = EcampusSession(session=MagicMock())
    fresh_session = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._cached_sessions[None] = stale_session

    with patch.object(EcampusMoodleAuthService, '_login', return_value=fresh_session) as mock_login:
        result = service.create_session(force_refresh=True, stale=stale_session)

    assert result is fresh_session
    assert EcampusMoodleAuthService._cached_sessions[None] is fresh_session
    mock_login.assert_called_once()


def test_create_session_force_refresh_skips_relogin_when_cache_already_advanced() -> None:
    """다른 스레드가 이미 같은 만료를 감지해 캐시를 갱신해뒀다면, 재로그인하지 않고
    최신 캐시를 그대로 반환한다 (CAS 핵심 동작)."""
    service = EcampusMoodleAuthService()
    stale_session = EcampusSession(session=MagicMock())
    already_refreshed = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._cached_sessions[None] = already_refreshed

    with patch.object(EcampusMoodleAuthService, '_login') as mock_login:
        result = service.create_session(force_refresh=True, stale=stale_session)

    assert result is already_refreshed
    mock_login.assert_not_called()


def test_create_session_records_failure_and_skips_relogin_within_backoff() -> None:
    """로그인 실패 직후 즉시 재시도하면 계정 잠금 위험이 있으므로, backoff 기간 내에는
    재로그인을 시도하지 않고 None을 반환한다."""
    service = EcampusMoodleAuthService()

    with patch.object(EcampusMoodleAuthService, '_login', return_value=None) as mock_login:
        result1 = service.create_session()
        assert result1 is None
        mock_login.assert_called_once()

        result2 = service.create_session(force_refresh=True, stale=None)
        assert result2 is None
        mock_login.assert_called_once()


def test_create_session_retries_login_after_backoff_elapses() -> None:
    service = EcampusMoodleAuthService()
    fresh_session = EcampusSession(session=MagicMock())

    with (
        patch.object(EcampusMoodleAuthService, '_login', side_effect=[None, fresh_session]) as mock_login,
        patch('apps.sejong.lecture.services.ecampus_auth.time.monotonic', side_effect=[0.0, 1000.0]),
    ):
        result1 = service.create_session()
        assert result1 is None

        result2 = service.create_session(force_refresh=True, stale=None)

    assert result2 is fresh_session
    assert mock_login.call_count == 2


def test_login_returns_none_when_credentials_missing(settings) -> None:
    settings.SEJONG_STUDENT_ID = ''
    settings.SEJONG_PASSWORD = ''
    service = EcampusMoodleAuthService()

    assert service._login() is None


def test_create_session_does_not_set_backoff_on_network_error() -> None:
    """네트워크 오류(타임아웃/5xx)는 자격증명 거부가 아니므로 backoff를 걸면 안 된다."""
    service = EcampusMoodleAuthService()

    with patch.object(EcampusMoodleAuthService, '_login', side_effect=_NetworkLoginError):
        result1 = service.create_session()

    assert result1 is None
    assert None not in EcampusMoodleAuthService._last_login_failure_times

    fresh_session = EcampusSession(session=MagicMock())
    with patch.object(EcampusMoodleAuthService, '_login', return_value=fresh_session) as mock_login:
        result2 = service.create_session(force_refresh=True, stale=None)

    assert result2 is fresh_session
    mock_login.assert_called_once()


def test_create_session_sets_backoff_only_on_credential_rejection() -> None:
    """자격증명이 실제로 거부된 경우(_login()이 None 반환)에만 backoff가 걸린다."""
    service = EcampusMoodleAuthService()

    with patch.object(EcampusMoodleAuthService, '_login', return_value=None):
        service.create_session()

    assert EcampusMoodleAuthService._last_login_failure_times.get(None) is not None


def test_fetch_with_retry_returns_result_without_retry_when_not_expired() -> None:
    service = EcampusMoodleAuthService()
    session = EcampusSession(session=MagicMock())
    operation = MagicMock(return_value=('결과', False))

    with patch.object(EcampusMoodleAuthService, 'create_session', return_value=session) as mock_create:
        result = service.fetch_with_retry(operation)

    assert result == '결과'
    mock_create.assert_called_once_with()
    operation.assert_called_once_with(session)


def test_fetch_with_retry_reauthenticates_once_and_succeeds_on_expiry() -> None:
    service = EcampusMoodleAuthService()
    stale_session = EcampusSession(session=MagicMock())
    fresh_session = EcampusSession(session=MagicMock())
    operation = MagicMock(side_effect=[(None, True), ('재시도 성공', False)])

    with patch.object(
        EcampusMoodleAuthService, 'create_session', side_effect=[stale_session, fresh_session],
    ) as mock_create:
        result = service.fetch_with_retry(operation)

    assert result == '재시도 성공'
    assert mock_create.call_count == 2
    mock_create.assert_any_call(force_refresh=True, stale=stale_session)
    assert operation.call_count == 2


def test_fetch_with_retry_returns_none_when_still_expired_after_reauth() -> None:
    service = EcampusMoodleAuthService()
    stale_session = EcampusSession(session=MagicMock())
    fresh_session = EcampusSession(session=MagicMock())
    operation = MagicMock(side_effect=[(None, True), (None, True)])

    with patch.object(
        EcampusMoodleAuthService, 'create_session', side_effect=[stale_session, fresh_session],
    ):
        result = service.fetch_with_retry(operation)

    assert result is None
    assert operation.call_count == 2


def test_fetch_with_retry_returns_none_when_initial_login_fails() -> None:
    service = EcampusMoodleAuthService()
    operation = MagicMock()

    with patch.object(EcampusMoodleAuthService, 'create_session', return_value=None):
        result = service.fetch_with_retry(operation)

    assert result is None
    operation.assert_not_called()


def test_fetch_with_retry_returns_none_when_reauth_fails() -> None:
    service = EcampusMoodleAuthService()
    stale_session = EcampusSession(session=MagicMock())
    operation = MagicMock(return_value=(None, True))

    with patch.object(
        EcampusMoodleAuthService, 'create_session', side_effect=[stale_session, None],
    ):
        result = service.fetch_with_retry(operation)

    assert result is None
    assert operation.call_count == 1


def _create_account(label: str = '친구', student_id: str = '20230001', password: str = 'friend-pw-1') -> SejongAccount:
    return SejongAccount.objects.create(label=label, student_id=student_id, password=password)


def test_sessions_are_cached_separately_per_account() -> None:
    sessions = {key: EcampusSession(session=MagicMock()) for key in (1, 2, None)}

    def fake_login(self: EcampusMoodleAuthService) -> EcampusSession:
        return sessions[self._account_id]

    with patch.object(EcampusMoodleAuthService, '_login', autospec=True, side_effect=fake_login) as mock_login:
        for key in (1, 2, None):
            assert EcampusMoodleAuthService(key).create_session() is sessions[key]
        assert mock_login.call_count == 3
        for key in (1, 2, None):
            assert EcampusMoodleAuthService(key).create_session() is sessions[key]
        assert mock_login.call_count == 3


def test_login_failure_backoff_does_not_block_other_accounts() -> None:
    def fake_login(self: EcampusMoodleAuthService) -> EcampusSession | None:
        if self._account_id == 1:
            return None
        return EcampusSession(session=MagicMock())

    with patch.object(EcampusMoodleAuthService, '_login', autospec=True, side_effect=fake_login) as mock_login:
        assert EcampusMoodleAuthService(1).create_session() is None
        assert EcampusMoodleAuthService(2).create_session() is not None
        assert EcampusMoodleAuthService().create_session() is not None
        assert mock_login.call_count == 3

        assert EcampusMoodleAuthService(1).create_session() is None
        assert mock_login.call_count == 3


def test_force_refresh_only_replaces_own_account_session() -> None:
    session_one = EcampusSession(session=MagicMock())
    session_two = EcampusSession(session=MagicMock())
    fresh_one = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._cached_sessions[1] = session_one
    EcampusMoodleAuthService._cached_sessions[2] = session_two

    with patch.object(EcampusMoodleAuthService, '_login', return_value=fresh_one):
        result = EcampusMoodleAuthService(1).create_session(force_refresh=True, stale=session_one)

    assert result is fresh_one
    assert EcampusMoodleAuthService._cached_sessions[1] is fresh_one
    assert EcampusMoodleAuthService._cached_sessions[2] is session_two


def test_resolve_credentials_uses_settings_for_default_account(settings) -> None:
    settings.SEJONG_STUDENT_ID = '19990001'
    settings.SEJONG_PASSWORD = 'owner-pw'

    assert EcampusMoodleAuthService()._resolve_credentials() == ('19990001', 'owner-pw')


@pytest.mark.django_db
def test_resolve_credentials_uses_database_row_for_account() -> None:
    account = _create_account(student_id='20230002', password='db-pw')

    assert EcampusMoodleAuthService(account.pk)._resolve_credentials() == ('20230002', 'db-pw')


@pytest.mark.django_db
def test_resolve_credentials_returns_none_for_missing_account() -> None:
    account = _create_account()
    missing_id = account.pk
    account.delete()

    assert EcampusMoodleAuthService(missing_id)._resolve_credentials() is None


@pytest.mark.django_db
def test_saving_account_evicts_cached_session_and_backoff() -> None:
    account = _create_account()
    other_session = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._cached_sessions[account.pk] = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._last_login_failure_times[account.pk] = 1.0
    EcampusMoodleAuthService._cached_sessions[-1] = other_session
    EcampusMoodleAuthService._last_login_failure_times[-1] = 2.0

    account.password = 'changed-pw'
    account.save()

    assert account.pk not in EcampusMoodleAuthService._cached_sessions
    assert account.pk not in EcampusMoodleAuthService._last_login_failure_times
    assert EcampusMoodleAuthService._cached_sessions[-1] is other_session
    assert EcampusMoodleAuthService._last_login_failure_times[-1] == 2.0


@pytest.mark.django_db
def test_deleting_account_evicts_cached_session() -> None:
    account = _create_account()
    other_session = EcampusSession(session=MagicMock())
    account_pk = account.pk
    EcampusMoodleAuthService._cached_sessions[account_pk] = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._last_login_failure_times[account_pk] = 1.0
    EcampusMoodleAuthService._cached_sessions[-1] = other_session

    account.delete()

    assert account_pk not in EcampusMoodleAuthService._cached_sessions
    assert account_pk not in EcampusMoodleAuthService._last_login_failure_times
    assert EcampusMoodleAuthService._cached_sessions[-1] is other_session


@pytest.mark.django_db
def test_login_posts_account_credentials() -> None:
    account = _create_account(student_id='20230003', password='post-pw')

    with patch('apps.sejong.lecture.services.ecampus_auth.requests.Session') as mock_session_class:
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = _make_response(
            url='https://ecampus.sejong.ac.kr/',
            text='<a href="logout.php">로그아웃</a>',
        )
        result = EcampusMoodleAuthService(account.pk)._login()

    assert result is not None
    posted_data = mock_session.post.call_args.kwargs['data']
    assert posted_data['username'] == '20230003'
    assert posted_data['password'] == 'post-pw'


@pytest.mark.django_db
def test_failed_login_does_not_log_password(caplog: pytest.LogCaptureFixture) -> None:
    account = _create_account(password='secret-never-logged')

    with (
        caplog.at_level(logging.DEBUG),
        patch('apps.sejong.lecture.services.ecampus_auth.requests.Session') as mock_session_class,
    ):
        mock_session_class.return_value.post.return_value = _make_response(
            url='https://ecampus.sejong.ac.kr/login/index.php',
            text='로그인 실패',
        )
        assert EcampusMoodleAuthService(account.pk)._login() is None

    assert 'secret-never-logged' not in caplog.text
