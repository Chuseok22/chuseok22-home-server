from django import template

register = template.Library()

_SIMPLE_ICONS_CDN = 'https://cdn.simpleicons.org/'

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
