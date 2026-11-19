import re

from apps.site.models import ConnectProfile

_LINE_BREAK_PATTERN = re.compile(r'\r\n|\r|\n')


def _escape_vcard_text(value: str) -> str:
    """vCard 텍스트 값 이스케이프. 줄바꿈을 리터럴 `\\n`으로 바꿔 속성 줄 주입을 막는다."""
    escaped = value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
    return _LINE_BREAK_PATTERN.sub(r'\\n', escaped)


def _strip_line_breaks(value: str) -> str:
    # TEL·EMAIL·URL은 이스케이프 대상이 아니므로 줄바꿈만 제거한다.
    return _LINE_BREAK_PATTERN.sub('', value)


def build_vcard(profile: ConnectProfile, website_url: str) -> str:
    """ConnectProfile을 vCard 3.0 문자열로 만든다. 마지막 단어를 성(family)으로 처리한다."""
    words = profile.english_name.split()
    family = words[-1] if words else ''
    given = ' '.join(words[:-1])

    lines = [
        'BEGIN:VCARD',
        'VERSION:3.0',
        f'N:{_escape_vcard_text(family)};{_escape_vcard_text(given)};;;',
        f'FN:{_escape_vcard_text(profile.english_name)}',
    ]
    if profile.title_lines:
        lines.append(f'TITLE:{_escape_vcard_text(", ".join(profile.title_lines))}')
    if profile.phone:
        lines.append(f'TEL;TYPE=CELL:{_strip_line_breaks(profile.phone)}')
    if profile.email:
        lines.append(f'EMAIL;TYPE=INTERNET:{_strip_line_breaks(profile.email)}')
    lines.append(f'URL:{_strip_line_breaks(website_url)}')
    lines.append('END:VCARD')
    return '\r\n'.join(lines) + '\r\n'
