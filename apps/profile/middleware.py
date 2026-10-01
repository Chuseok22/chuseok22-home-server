import logging
from collections.abc import Callable
from datetime import date

from django.conf import settings
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.profile.services.visitor_counter import (
    VISITED_COOKIE_NAME,
    record_visit,
    seconds_until_next_midnight,
    should_count_visit,
)

logger = logging.getLogger(__name__)


class VisitorCountMiddleware:
    """`site` 네임스페이스 페이지의 일자별 방문자를 집계하고 하루 1회 중복 방지 쿠키를 심는다.

    URL이 뷰에 매핑된 요청만 process_view에 도달하므로 404 스캐너 트래픽은 자연히 제외된다.
    뷰 실행 전에 집계하므로 첫 방문자가 홈을 렌더링할 때 본인 방문이 숫자에 반영된다.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        counted_date: date | None = getattr(request, 'visit_counted_date', None)
        if counted_date is not None:
            response.set_cookie(
                VISITED_COOKIE_NAME,
                counted_date.isoformat(),
                max_age=seconds_until_next_midnight(timezone.now()),
                httponly=True,
                samesite='Lax',
                secure=settings.SESSION_COOKIE_SECURE,
            )
        return response

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., HttpResponse],
        view_args: tuple,
        view_kwargs: dict,
    ) -> None:
        if request.resolver_match.namespace != 'site':
            return None
        today = timezone.localdate()
        if not should_count_visit(
            method=request.method,
            visited_cookie_value=request.COOKIES.get(VISITED_COOKIE_NAME),
            is_staff=request.user.is_staff,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            today=today,
        ):
            return None
        try:
            record_visit(today)
        except DatabaseError:
            logger.exception('방문자 집계 실패 — 페이지 응답에는 영향을 주지 않는다')
            return None
        request.visit_counted_date = today
        return None
