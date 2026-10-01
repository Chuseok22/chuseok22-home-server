from datetime import date, datetime, timedelta
from typing import NamedTuple

from django.db.models import F, Sum
from django.utils import timezone

from apps.profile.models import DailyVisitor

VISITED_COOKIE_NAME = 'visited_today'

# 개인 사이트 규모에서는 키워드 목록으로 충분하다고 판단해 외부 봇 판별 패키지를 쓰지 않는다.
_BOT_USER_AGENT_KEYWORDS = (
    'bot', 'crawler', 'spider', 'slurp', 'preview', 'facebookexternalhit',
    'curl', 'wget', 'python-requests', 'httpx', 'headless',
)


class VisitCounts(NamedTuple):
    today: int
    total: int


def is_bot_user_agent(user_agent: str) -> bool:
    lowered_user_agent = user_agent.lower()
    return any(keyword in lowered_user_agent for keyword in _BOT_USER_AGENT_KEYWORDS)


def should_count_visit(method: str, visited_cookie_value: str | None, is_staff: bool, user_agent: str,
                       today: date) -> bool:
    """오늘 이 방문자를 집계해야 하는지 판단한다. 쿠키 값이 오늘 날짜와 정확히 같을 때만 이미 센 것으로 본다.

    서비스 계층은 HTTP 객체를 받지 않으므로 요청에서 뽑은 원시값만 받는다.
    """
    if method != 'GET':
        return False
    if visited_cookie_value == today.isoformat():
        return False
    if is_staff:
        return False
    return not is_bot_user_agent(user_agent)


def record_visit(today: date) -> None:
    # get_or_create는 동시 요청 시 unique 충돌을 내부에서 재조회로 처리하고, 증가는 F()로 DB에서 원자적으로 수행한다.
    DailyVisitor.objects.get_or_create(date=today)
    DailyVisitor.objects.filter(date=today).update(count=F('count') + 1)


def get_visit_counts(today: date) -> VisitCounts:
    today_count = DailyVisitor.objects.filter(date=today).values_list('count', flat=True).first() or 0
    total_count = DailyVisitor.objects.aggregate(total=Sum('count'))['total'] or 0
    return VisitCounts(today=today_count, total=total_count)


def seconds_until_next_midnight(now: datetime) -> int:
    """다음 KST 자정까지 남은 초. max_age=0이면 쿠키가 즉시 삭제되므로 최소 1을 보장한다."""
    local_now = timezone.localtime(now)
    next_midnight = (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((next_midnight - local_now).total_seconds()))
