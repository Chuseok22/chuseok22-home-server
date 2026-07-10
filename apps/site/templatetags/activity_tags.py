from django import template

register = template.Library()

_EVENT_ICON_MAP = {
    'PushEvent': '📝',
    'PullRequestEvent': '🔀',
    'PullRequestReviewEvent': '👀',
    'CreateEvent': '🎉',
    'ReleaseEvent': '🚀',
    'IssuesEvent': '🐛',
}

_DEFAULT_ICON = '📌'


@register.filter
def activity_icon(event_type: str) -> str:
    """event_type을 표시용 이모지로 매핑한다. 알 수 없는 유형은 기본 아이콘을 반환한다."""
    return _EVENT_ICON_MAP.get(event_type, _DEFAULT_ICON)


@register.filter
def contribution_level_class(count: int) -> str:
    """커밋 수를 5단계 DaisyUI 색상 클래스로 매핑한다 (GitHub 잔디의 초록 계단식 표현)."""
    if count == 0:
        return 'bg-base-300'
    if count <= 3:
        return 'bg-success/30'
    if count <= 6:
        return 'bg-success/55'
    if count <= 9:
        return 'bg-success/80'
    return 'bg-success'
