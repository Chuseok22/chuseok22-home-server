import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_MAX_ATTEMPTS = 3
_RETRY_STATUS_CODES = (404, 502, 503, 504)
_BACKOFF_FACTOR = 1


class _ExponentialBackoffRetry(Retry):
    """재시도 대기시간을 1초 → 2초로 늘리는 Retry"""

    def get_backoff_time(self) -> float:
        # urllib3 2.x 기본 구현은 첫 재시도를 무조건 대기 0으로 처리해 backoff_factor를 어떻게
        # 줘도 1초 → 2초가 나오지 않으므로, 합의된 정책에 맞게 직접 계산한다.
        if not self.history:
            return 0.0
        return float(self.backoff_factor * 2 ** (len(self.history) - 1))


def build_retry_session() -> requests.Session:
    """일시적 404·5xx 응답과 연결 오류를 최대 _MAX_ATTEMPTS회까지 재시도하는 세션을 만든다."""
    retry = _ExponentialBackoffRetry(
        total=_MAX_ATTEMPTS - 1,
        status_forcelist=_RETRY_STATUS_CODES,
        backoff_factor=_BACKOFF_FACTOR,
        # 재시도 소진 시 MaxRetryError 대신 마지막 응답을 반환해 raise_for_status()가 실제 상태코드를 로그에 남기게 한다.
        raise_on_status=False,
        # 기본값은 Retry-After 초만큼 상한 없이 대기하므로 최악 지연을 예측 가능하게 유지하려고 끈다.
        respect_retry_after_header=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session
