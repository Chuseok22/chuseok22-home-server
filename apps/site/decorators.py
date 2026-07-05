from functools import wraps
from typing import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def owner_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """로그인한 사이트 소유자(is_staff)만 접근을 허용한다."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not (request.user.is_authenticated and request.user.is_staff):
            raise PermissionDenied('이 기능은 사이트 소유자만 사용할 수 있습니다.')
        return view_func(request, *args, **kwargs)

    return wrapper
