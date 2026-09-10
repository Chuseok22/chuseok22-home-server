from unittest.mock import MagicMock, patch

import pytest

from apps.sejong.lecture.services.ecampus_auth import (
    EcampusMoodleAuthService,
    EcampusSession,
    _is_login_successful,
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


@pytest.fixture(autouse=True)
def _reset_session_cache():
    """클래스 레벨 세션 캐시/backoff 상태는 테스트 간 상태가 누출되므로 매 테스트 전후로 리셋한다."""
    EcampusMoodleAuthService._cached_session = None
    EcampusMoodleAuthService._last_login_failure_at = None
    yield
    EcampusMoodleAuthService._cached_session = None
    EcampusMoodleAuthService._last_login_failure_at = None


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
    EcampusMoodleAuthService._cached_session = stale_session

    with patch.object(EcampusMoodleAuthService, '_login', return_value=fresh_session) as mock_login:
        result = service.create_session(force_refresh=True, stale=stale_session)

    assert result is fresh_session
    assert EcampusMoodleAuthService._cached_session is fresh_session
    mock_login.assert_called_once()


def test_create_session_force_refresh_skips_relogin_when_cache_already_advanced() -> None:
    """다른 스레드가 이미 같은 만료를 감지해 캐시를 갱신해뒀다면, 재로그인하지 않고
    최신 캐시를 그대로 반환한다 (CAS 핵심 동작)."""
    service = EcampusMoodleAuthService()
    stale_session = EcampusSession(session=MagicMock())
    already_refreshed = EcampusSession(session=MagicMock())
    EcampusMoodleAuthService._cached_session = already_refreshed

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
