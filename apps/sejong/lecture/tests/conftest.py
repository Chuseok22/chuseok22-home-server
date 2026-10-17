from collections.abc import Iterator

import pytest

from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService


@pytest.fixture(autouse=True)
def _reset_ecampus_auth_state() -> Iterator[None]:
    """클래스 레벨 세션 캐시/backoff 상태는 테스트 간에 새므로 매 테스트 전후로 비운다."""
    EcampusMoodleAuthService._cached_sessions.clear()
    EcampusMoodleAuthService._last_login_failure_times.clear()
    yield
    EcampusMoodleAuthService._cached_sessions.clear()
    EcampusMoodleAuthService._last_login_failure_times.clear()
