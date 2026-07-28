import re
from functools import lru_cache
from pathlib import Path

from django import template
from django.contrib.staticfiles import finders
from django.utils.html import format_html

from apps.core.icons import resolve_icon_relpath

register = template.Library()

_ANY_PATH_TAG_RE = re.compile(r'<path\b')
_PATH_D_ATTR_RE = re.compile(r'<path\b[^>]*\bd="([^"]+)"')


@lru_cache(maxsize=512)
def _read_vendored_svg_path_data(relpath: str) -> str | None:
    """벤더링된 SVG 파일에서 <path d="..."> 값을 추출한다. 결과는 프로세스 생존 기간 동안 캐시한다.

    <path> 엘리먼트가 정확히 1개인 SVG(Simple Icons가 보장하는 형식, other-brands도 이 형식으로
    정규화하도록 요구함 — README 참고)만 지원한다. 그 외 형식(다중 path, viewBox가 다른 원본을
    그대로 벤더링한 경우 등)을 우리 24x24 wrapper에 억지로 끼워 넣으면 아이콘이 깨지므로,
    지원하지 않는 형식이면 None을 반환해 아이콘을 아예 그리지 않는다 — 잘못된 형식의 파일이
    잘못 벤더링되더라도 "깨져 보이는 아이콘"이 아니라 "빈 자리"가 되게 하는 방어적 설계다.
    """
    absolute_path = finders.find(relpath)
    if not absolute_path:
        return None
    svg_source = Path(absolute_path).read_text(encoding='utf-8')
    if len(_ANY_PATH_TAG_RE.findall(svg_source)) != 1:
        return None
    match = _PATH_D_ATTR_RE.search(svg_source)
    return match.group(1) if match else None


@register.simple_tag
def brand_icon(slug: str, css_class: str = 'w-4 h-4 shrink-0') -> str:
    """벤더링된 Simple Icons/other-brands SVG를 fill="currentColor" wrapper로 inline 렌더링한다.

    슬러그가 벤더링된 세트에 없으면(정상 경로에서는 Skill.clean()이 이미 막지만, 템플릿
    직접 호출 등 방어적으로) 빈 문자열을 반환해 깨진 아이콘이 노출되지 않게 한다. 장식용
    아이콘이므로 aria-hidden="true"를 붙이고, 접근 가능한 이름은 호출하는 쪽의 <a aria-label>에
    맡긴다.
    """
    relpath = resolve_icon_relpath(slug)
    if relpath is None:
        return ''
    path_data = _read_vendored_svg_path_data(relpath)
    if path_data is None:
        return ''
    return format_html(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" '
        'aria-hidden="true" class="{}"><path d="{}"/></svg>',
        css_class,
        path_data,
    )
