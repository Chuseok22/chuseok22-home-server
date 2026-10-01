from django import template

from apps.profile.services.visitor_counter import DailyCount

register = template.Library()

_SIMPLE_ICONS_CDN = 'https://cdn.simpleicons.org/'

# 방문자 스파크라인 SVG 좌표계. 위·아래 8px 여백을 두어 점의 외곽 원이 잘리지 않게 한다.
_SPARKLINE_WIDTH = 256
_SPARKLINE_HEIGHT = 64
_SPARKLINE_TOP = 8
_SPARKLINE_BOTTOM = 56

_ACTIVITY_LINK_ICONS = {
    'official': ('공식 페이지', 'https://cdn.jsdelivr.net/npm/heroicons@2/24/outline/globe-alt.svg'),
    'github': ('GitHub', 'github'),
    'youtube': ('YouTube', 'youtube'),
    'instagram': ('Instagram', 'instagram'),
    'linkedin': ('LinkedIn', 'linkedin'),
    'presentation': ('발표자료', 'https://cdn.jsdelivr.net/npm/heroicons@2/24/outline/document-text.svg'),
    'article': ('관련기사', 'https://cdn.jsdelivr.net/npm/heroicons@2/24/outline/newspaper.svg'),
    'other': ('링크', 'https://cdn.jsdelivr.net/npm/heroicons@2/24/outline/link.svg'),
}


@register.filter
def skill_icon_url(icon_slug: str) -> str:
    """icon_slug가 완전한 URL이면 그대로 반환하고, 아니면 Simple Icons CDN URL로 변환한다.

    Simple Icons에 없는 브랜드(Java, AWS 등 상표권 이슈로 미등록된 아이콘)는
    다른 아이콘 CDN(devicon 등)의 전체 URL을 icon_slug에 직접 넣어 사용할 수 있다.
    """
    if icon_slug.startswith('http://') or icon_slug.startswith('https://'):
        return icon_slug
    return f'{_SIMPLE_ICONS_CDN}{icon_slug}'


@register.filter
def activity_link_icon(link_type: str) -> dict:
    """활동 링크 type을 라벨·아이콘 URL 딕셔너리로 변환한다. 정의되지 않은 type은 'other'로 대체한다."""
    label, icon = _ACTIVITY_LINK_ICONS.get(link_type, _ACTIVITY_LINK_ICONS['other'])
    return {'label': label, 'icon_url': icon if icon.startswith('http') else skill_icon_url(icon)}


def _visit_day_label(visit: DailyCount, is_today: bool) -> str:
    return '오늘' if is_today else f'{visit.date.month}/{visit.date.day}'


@register.inclusion_tag('site/partials/visitor_sparkline.html')
def visitor_sparkline(recent_visits: list[DailyCount]) -> dict:
    """최근 일자별 방문 수를 SVG 스파크라인 좌표로 변환한다. 최댓값이 위쪽 여백 선에 닿고, 모두 0이면 바닥선이 된다."""
    peak = max(max((visit.count for visit in recent_visits), default=0), 1)
    horizontal_step = _SPARKLINE_WIDTH / max(len(recent_visits) - 1, 1)
    plot_height = _SPARKLINE_BOTTOM - _SPARKLINE_TOP
    points = [
        (round(index * horizontal_step), round(_SPARKLINE_BOTTOM - visit.count / peak * plot_height))
        for index, visit in enumerate(recent_visits)
    ]
    line_points = ' '.join(f'{x},{y}' for x, y in points)
    last_index = len(recent_visits) - 1
    label_parts = [
        f'{_visit_day_label(visit, is_today=index == last_index)} {visit.count}'
        for index, visit in enumerate(recent_visits)
    ]
    dot_x, dot_y = points[-1]
    return {
        'width': _SPARKLINE_WIDTH,
        'height': _SPARKLINE_HEIGHT,
        'line_points': line_points,
        'area_points': f'0,{_SPARKLINE_BOTTOM} {line_points} {_SPARKLINE_WIDTH},{_SPARKLINE_BOTTOM}',
        'dot_x': dot_x,
        'dot_y': dot_y,
        'label': f'최근 {len(recent_visits)}일 방문자: {", ".join(label_parts)}',
    }
