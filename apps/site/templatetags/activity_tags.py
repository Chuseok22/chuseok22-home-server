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
