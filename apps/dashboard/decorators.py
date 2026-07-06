from functools import wraps
from typing import Callable

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def dashboard_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """관리자 대시보드 접근 권한을 확인한다.

    미인증 사용자는 로그인 페이지로 리다이렉트하고(next 파라미터로 복귀),
    인증됐지만 is_staff가 아니면 403을 발생시킨다.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise PermissionDenied('이 기능은 관리자만 사용할 수 있습니다.')
        return view_func(request, *args, **kwargs)

    return wrapper
