import re

from django.contrib.staticfiles import finders

_ICON_SOURCE_DIRS = ('simple-icons', 'other-brands')
# 슬러그는 영문 소문자/숫자/점/하이픈/언더스코어만 허용한다. 슬래시를 원천 차단해 경로 순회
# (`../../etc/hosts` 등)로 finders.find()에 임의 경로가 전달되는 것을 막는다.
_VALID_SLUG_RE = re.compile(r'^[a-z0-9._-]+$')


def resolve_icon_relpath(slug: str) -> str | None:
    """벤더링된 아이콘 세트에서 슬러그에 해당하는 정적 파일의 상대 경로를 찾는다.

    Simple Icons 세트를 먼저 확인하고, 없으면 other-brands(개별 수동 벤더링)를 확인한다.
    슬러그 형식이 유효하지 않거나(경로 순회 문자 등) 둘 다 없으면 None을 반환한다.
    """
    if not slug or not _VALID_SLUG_RE.fullmatch(slug):
        return None
    for source_dir in _ICON_SOURCE_DIRS:
        relpath = f'core/icons/{source_dir}/{slug}.svg'
        if finders.find(relpath):
            return relpath
    return None


def is_valid_icon_slug(slug: str) -> bool:
    """슬러그가 벤더링된 아이콘 세트(Simple Icons 또는 other-brands)에 존재하는지 확인한다."""
    return resolve_icon_relpath(slug) is not None
