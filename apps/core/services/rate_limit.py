from django.core.cache import cache
from django.http import HttpRequest


def check_rate_limit(request: HttpRequest, key: str, limit: int, window_seconds: int) -> bool:
    """요청 IP 기준 고정 윈도(fixed window) rate limit을 확인한다.

    Redis 없이 Django 기본 LocMemCache(프로세스 인메모리)를 사용하므로, 여러 워커 프로세스에
    걸친 정확한 전역 카운트는 보장하지 않는다 — 명백한 남용을 줄이는 수준의 방어로 채택했다.

    이 특성 때문에 배포 프로세스 모델과 결합된다: gunicorn을 스케일링할 때 반드시
    `--threads`로만 늘려야 하며(Dockerfile CMD 참고) `--workers`를 늘리면 워커마다 별도의
    LocMemCache를 갖게 되어 IP당 제한이 사실상 `limit × workers`로 느슨해진다. Dockerfile을
    다른 이유로 수정하더라도 `--workers 1`은 유지해야 이 rate limit이 의도대로 동작한다.
    """
    ip = _get_client_ip(request)
    cache_key = f'rate_limit:{key}:{ip}'

    if cache.add(cache_key, 1, timeout=window_seconds):
        # 이 프로세스·이 윈도에서 첫 요청 — add()는 키가 없을 때만 원자적으로 성공한다.
        return True

    try:
        count = cache.incr(cache_key)
    except ValueError:
        # add()~incr() 사이 만료 경계에서 키가 이미 소멸된 드문 경우 — 새 윈도로 취급한다.
        cache.set(cache_key, 1, timeout=window_seconds)
        return True

    return count <= limit


def _get_client_ip(request: HttpRequest) -> str:
    return request.META.get('REMOTE_ADDR', 'unknown')
