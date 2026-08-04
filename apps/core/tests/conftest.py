import pytest


@pytest.fixture(autouse=True)
def _reset_job_lock():
    """apps.core.scheduler의 전역 실행 중 job_id 집합을 테스트마다 초기화한다.

    이 집합은 모듈 전역 상태라 한 테스트가 오염시키면 다른 테스트의 동시성 검증이
    거짓 성공/거짓 실패할 수 있어, 매 테스트 전후로 강제 초기화한다.
    """
    from apps.core.scheduler import _running_job_ids

    _running_job_ids.clear()
    yield
    _running_job_ids.clear()
