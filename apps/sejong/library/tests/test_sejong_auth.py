from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.sejong.library.services.sejong_auth import AuthSession, SejongLibraryAuthService, _extract_token_from_chain


def test_extract_token_from_chain_preserves_plus_character() -> None:
    response = SimpleNamespace(
        url=(
            'https://libseat.sejong.ac.kr/mobile/MA/seatMain.php'
            '?token=+aKUmmZWL3BNdNihPzVcfOS/7t5qtqNF3trT647vDKo%3D'
        ),
        history=[],
    )

    assert _extract_token_from_chain(response) == '+aKUmmZWL3BNdNihPzVcfOS/7t5qtqNF3trT647vDKo='


def test_extract_token_from_chain_returns_none_when_host_not_libseat() -> None:
    response = SimpleNamespace(
        url='https://portal.sejong.ac.kr/some/path?token=abc123',
        history=[],
    )

    assert _extract_token_from_chain(response) is None


def test_extract_token_from_chain_falls_back_to_history() -> None:
    response = SimpleNamespace(
        url='https://libseat.sejong.ac.kr/mobile/MA/seatMain.php',
        history=[
            SimpleNamespace(url='https://libseat.sejong.ac.kr/mobile/MA/seatMain.php?token=abc123'),
        ],
    )

    assert _extract_token_from_chain(response) == 'abc123'


def test_extract_token_from_chain_returns_none_when_no_token_param() -> None:
    response = SimpleNamespace(
        url='https://libseat.sejong.ac.kr/mobile/MA/seatMain.php',
        history=[],
    )

    assert _extract_token_from_chain(response) is None


def test_extract_token_from_chain_ignores_token_param_after_literal_question_mark() -> None:
    """쿼리 문자열에 리터럴 '?'가 중첩되어 나타나는 경우(예: 다른 파라미터 값에 포함된 URL),
    그 뒤의 'token='을 진짜 파라미터 경계로 착각해 매칭하지 않는다 - '&'로 구분되는
    진짜 token 파라미터만 추출한다."""
    response = SimpleNamespace(
        url=(
            'https://libseat.sejong.ac.kr/mobile/MA/seatMain.php'
            '?redirect=foo?token=fake&token=real'
        ),
        history=[],
    )

    assert _extract_token_from_chain(response) == 'real'


@pytest.fixture(autouse=True)
def _reset_session_cache():
    """클래스 레벨 세션 캐시는 테스트 간 상태가 누출되므로 매 테스트 전후로 리셋한다."""
    SejongLibraryAuthService._cached_session = None
    yield
    SejongLibraryAuthService._cached_session = None


def test_create_session_returns_cached_session_without_relogin() -> None:
    service = SejongLibraryAuthService()
    first_session = AuthSession(token='t1', session=MagicMock())

    with patch.object(SejongLibraryAuthService, '_login', return_value=first_session) as mock_login:
        result1 = service.create_session()
        result2 = service.create_session()

    assert result1 is first_session
    assert result2 is first_session
    mock_login.assert_called_once()


def test_create_session_force_refresh_relogins_when_stale_matches_cache() -> None:
    service = SejongLibraryAuthService()
    stale_session = AuthSession(token='stale', session=MagicMock())
    fresh_session = AuthSession(token='fresh', session=MagicMock())
    SejongLibraryAuthService._cached_session = stale_session

    with patch.object(SejongLibraryAuthService, '_login', return_value=fresh_session) as mock_login:
        result = service.create_session(force_refresh=True, stale=stale_session)

    assert result is fresh_session
    assert SejongLibraryAuthService._cached_session is fresh_session
    mock_login.assert_called_once()


def test_create_session_force_refresh_skips_relogin_when_cache_already_advanced() -> None:
    """다른 스레드가 이미 같은 만료를 감지해 캐시를 갱신해뒀다면, 재로그인하지 않고
    최신 캐시를 그대로 반환한다 (CAS 핵심 동작)."""
    service = SejongLibraryAuthService()
    stale_session = AuthSession(token='stale', session=MagicMock())
    already_refreshed = AuthSession(token='already-fresh', session=MagicMock())
    SejongLibraryAuthService._cached_session = already_refreshed

    with patch.object(SejongLibraryAuthService, '_login') as mock_login:
        result = service.create_session(force_refresh=True, stale=stale_session)

    assert result is already_refreshed
    mock_login.assert_not_called()


def test_fetch_with_retry_returns_result_without_retry_when_not_expired() -> None:
    service = SejongLibraryAuthService()
    auth_session = AuthSession(token='t', session=MagicMock())

    def operation(session: AuthSession) -> tuple[str, bool]:
        assert session is auth_session
        return 'ok', False

    with patch.object(SejongLibraryAuthService, '_login', return_value=auth_session):
        result = service.fetch_with_retry(operation)

    assert result == 'ok'


def test_fetch_with_retry_retries_once_with_fresh_session_when_expired() -> None:
    service = SejongLibraryAuthService()
    stale_session = AuthSession(token='stale', session=MagicMock())
    fresh_session = AuthSession(token='fresh', session=MagicMock())
    calls: list[AuthSession] = []

    def operation(session: AuthSession) -> tuple[str, bool]:
        calls.append(session)
        if session is stale_session:
            return 'stale-result', True
        return 'fresh-result', False

    with patch.object(
        SejongLibraryAuthService, '_login', side_effect=[stale_session, fresh_session],
    ):
        result = service.fetch_with_retry(operation)

    assert result == 'fresh-result'
    assert calls == [stale_session, fresh_session]


def test_fetch_with_retry_returns_none_when_reauth_fails_after_expiry() -> None:
    service = SejongLibraryAuthService()
    stale_session = AuthSession(token='stale', session=MagicMock())

    def operation(session: AuthSession) -> tuple[str, bool]:
        return 'stale-result', True

    with patch.object(SejongLibraryAuthService, '_login', side_effect=[stale_session, None]):
        result = service.fetch_with_retry(operation)

    assert result is None


def test_fetch_with_retry_returns_none_when_still_expired_after_retry() -> None:
    """재인증에는 성공했지만 새 세션으로도 만료가 감지되면, 두 번째 만료를 무시하고
    부정확한 placeholder 결과를 돌려주는 대신 None(인증 상태 이상)을 반환한다."""
    service = SejongLibraryAuthService()
    stale_session = AuthSession(token='stale', session=MagicMock())
    fresh_session = AuthSession(token='fresh', session=MagicMock())

    def operation(session: AuthSession) -> tuple[str, bool]:
        return 'placeholder', True

    with patch.object(
        SejongLibraryAuthService, '_login', side_effect=[stale_session, fresh_session],
    ) as mock_login:
        result = service.fetch_with_retry(operation)

    assert result is None
    assert mock_login.call_count == 2


def test_fetch_with_retry_returns_none_when_initial_login_fails() -> None:
    service = SejongLibraryAuthService()
    operation = MagicMock()

    with patch.object(SejongLibraryAuthService, '_login', return_value=None):
        result = service.fetch_with_retry(operation)

    assert result is None
    operation.assert_not_called()
