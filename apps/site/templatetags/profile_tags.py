from django import template

register = template.Library()

_SIMPLE_ICONS_CDN = 'https://cdn.simpleicons.org/'


@register.filter
def skill_icon_url(icon_slug: str) -> str:
    """icon_slug가 완전한 URL이면 그대로 반환하고, 아니면 Simple Icons CDN URL로 변환한다.

    Simple Icons에 없는 브랜드(Java, AWS 등 상표권 이슈로 미등록된 아이콘)는
    다른 아이콘 CDN(devicon 등)의 전체 URL을 icon_slug에 직접 넣어 사용할 수 있다.
    """
    if icon_slug.startswith('http://') or icon_slug.startswith('https://'):
        return icon_slug
    return f'{_SIMPLE_ICONS_CDN}{icon_slug}'
