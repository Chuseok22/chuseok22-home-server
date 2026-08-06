import html
import re

import bleach
import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

# 마크다운 렌더링 결과에서 허용할 태그·속성 화이트리스트.
# 본문은 사이트 소유자만 작성 가능하지만(Django Admin 또는 Ingest API), 저장된 HTML이
# 그대로 방문자에게 노출되므로 방어적으로 sanitize한다.
_ALLOWED_TAGS = [
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'em', 'del', 'code', 'pre',
    'ul', 'ol', 'li',
    'blockquote',
    'a', 'img',
    'video', 'source',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span',
]

_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
    'video': ['src', 'controls'],
    'source': ['src', 'type'],
    'div': ['class'],
    'pre': ['class', 'data-lang'],
    'span': ['class'],
}

# 언어명 문자 집합은 python-markdown fenced_code 확장이 실제로 허용하는 [\w#.+-]와 동일하게
# 맞춘다(예: c++, c#, objective-c 같은 언어명도 인식해야 하므로 \w만으로는 부족하다).
_FENCED_CODE_BLOCK_PATTERN = re.compile(r'```([\w#.+-]*)\n(.*?)\n```', re.DOTALL)
_PYGMENTS_FORMATTER = HtmlFormatter(style='github-dark', cssclass='codehilite')


def _highlight_code_block(lang: str, code: str) -> str:
    """fenced code block 하나를 Pygments로 하이라이팅하고 <pre>에 data-lang 속성을 채워 넣는다."""
    label = lang or 'text'
    try:
        lexer = get_lexer_by_name(lang) if lang else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    highlighted = highlight(code, lexer, _PYGMENTS_FORMATTER)
    return highlighted.replace('<pre>', f'<pre data-lang="{label}">', 1)


def render_markdown(text: str) -> str:
    """Markdown 원문을 HTML로 변환한 뒤 허용된 태그·속성만 남기고 sanitize한다.

    fenced code block(``` ... ```)은 markdown.markdown() 호출 전에 모두 직접 추출해
    플레이스홀더로 치환한다. mermaid 블록은 Pygments가 렉서를 지원하지 않으므로 원본
    텍스트를 그대로 보존하고, 나머지는 Pygments로 직접 하이라이팅해 <pre>에 data-lang
    속성을 채워 넣는다(코드블록 헤더 JS가 이 속성으로 언어 라벨을 표시한다). 이렇게 모든
    fenced block을 렌더링 전에 미리 처리해두면, 렌더링 결과에서 위치 기반으로 다시 찾아
    매칭할 필요가 없어 순서 불일치로 인한 오류(예: 본문에 우연히 같은 클래스명의 raw HTML이
    섞여 있는 경우) 걱정 없이 안전하게 대응할 수 있다.
    """
    placeholders: dict[str, str] = {}

    def _extract_fenced_block(match: re.Match[str]) -> str:
        lang = match.group(1)
        code = match.group(2)
        key = f'BLOCKPLACEHOLDER{len(placeholders)}'
        if lang == 'mermaid':
            placeholders[key] = f'<pre class="mermaid">{html.escape(code)}</pre>'
        else:
            placeholders[key] = _highlight_code_block(lang, code)
        return f'\n\n{key}\n\n'

    processed_text = _FENCED_CODE_BLOCK_PATTERN.sub(_extract_fenced_block, text)
    rendered_html = markdown.markdown(processed_text, extensions=['fenced_code', 'tables'])
    for key, block_html in placeholders.items():
        rendered_html = rendered_html.replace(f'<p>{key}</p>', block_html)

    return bleach.clean(rendered_html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES, strip=True)
