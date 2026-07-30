import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.core.services.rate_limit import check_rate_limit


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def factory() -> RequestFactory:
    return RequestFactory()


def test_한도_이내면_계속_허용한다(factory: RequestFactory) -> None:
    request = factory.post('/chat/', REMOTE_ADDR='1.2.3.4')

    results = [check_rate_limit(request, key='chat', limit=5, window_seconds=60) for _ in range(5)]

    assert all(results)


def test_한도_초과시_거부한다(factory: RequestFactory) -> None:
    request = factory.post('/chat/', REMOTE_ADDR='1.2.3.4')

    for _ in range(5):
        check_rate_limit(request, key='chat', limit=5, window_seconds=60)
    sixth = check_rate_limit(request, key='chat', limit=5, window_seconds=60)

    assert sixth is False


def test_다른_ip는_독립적으로_카운트된다(factory: RequestFactory) -> None:
    request_a = factory.post('/chat/', REMOTE_ADDR='1.2.3.4')
    request_b = factory.post('/chat/', REMOTE_ADDR='5.6.7.8')

    for _ in range(5):
        check_rate_limit(request_a, key='chat', limit=5, window_seconds=60)
    result_b = check_rate_limit(request_b, key='chat', limit=5, window_seconds=60)

    assert result_b is True


def test_X_Forwarded_For_헤더는_신뢰하지_않고_REMOTE_ADDR을_사용한다(factory: RequestFactory) -> None:
    # 같은 REMOTE_ADDR에서 X-Forwarded-For만 바꿔 요청해도 우회되면 안 된다.
    request_1 = factory.post('/chat/', REMOTE_ADDR='9.9.9.9', HTTP_X_FORWARDED_FOR='1.1.1.1')
    request_2 = factory.post('/chat/', REMOTE_ADDR='9.9.9.9', HTTP_X_FORWARDED_FOR='2.2.2.2')

    for _ in range(5):
        check_rate_limit(request_1, key='chat', limit=5, window_seconds=60)
    result = check_rate_limit(request_2, key='chat', limit=5, window_seconds=60)

    assert result is False


def test_다른_key는_독립적으로_카운트된다(factory: RequestFactory) -> None:
    request = factory.post('/chat/', REMOTE_ADDR='1.2.3.4')

    for _ in range(5):
        check_rate_limit(request, key='chat', limit=5, window_seconds=60)
    other_key_result = check_rate_limit(request, key='other-endpoint', limit=5, window_seconds=60)

    assert other_key_result is True


def test_incr_호출_시점에_키가_만료되어_ValueError가_발생해도_예외없이_새_윈도로_처리한다(
    factory: RequestFactory, monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = factory.post('/chat/', REMOTE_ADDR='1.2.3.4')
    check_rate_limit(request, key='chat', limit=5, window_seconds=60)  # cache.add()로 카운터 생성(1)

    # add()~incr() 사이 만료 경계를 흉내낸다: 다음 호출이 실제로 cache.incr()에서 ValueError를
    # 만나도록 incr을 직접 대체한다(단순히 cache.clear()만 하면 두 번째 호출도 add()가 다시
    # 성공해버려 except 분기를 전혀 거치지 않으므로, 이렇게 해야 의도한 분기를 검증할 수 있다).
    def _raise_value_error(*args: object, **kwargs: object) -> int:
        raise ValueError('key not found')

    monkeypatch.setattr('apps.core.services.rate_limit.cache.incr', _raise_value_error)

    result = check_rate_limit(request, key='chat', limit=5, window_seconds=60)

    assert result is True
