from django.core.cache import cache
from django.http import HttpRequest


def check_rate_limit(request: HttpRequest, key: str, limit: int, window_seconds: int) -> bool:
    """요청 IP 기준 고정 윈도(fixed window) rate limit을 확인한다.

    Redis 없이 Django 기본 LocMemCache(프로세스 인메모리)를 사용하므로, 여러 워커 프로세스에
    걸친 정확한 전역 카운트는 보장하지 않는다 — 명백한 남용을 줄이는 수준의 방어로 채택했다.
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
